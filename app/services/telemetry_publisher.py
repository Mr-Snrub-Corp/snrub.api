"""1Hz in-process telemetry publisher loop (Phase 2).

Ticks once a second: recomputes metrics via the existing controller, publishes
the full blob to ``snrub/reactor/metrics`` and retained per-metric alarm levels
to ``snrub/alarms/{metric}`` when a level changes. Runs as a FastAPI lifespan
task guarded by ``settings.MQTT_ENABLED``; ``/ws/telemetry`` is untouched.

Phase 3 moves this into a dedicated singleton simulator process (see
docs/roadmap.md "Process architecture (decided)"); the advisory-lock / single
-writer concern is deliberately out of scope here.
"""

import asyncio
import time
from logging import getLogger

import aiomqtt
from sqlmodel import Session

from app.controllers.telemetry import get_reactor_metrics
from app.core.config import settings
from app.db.database import engine
from app.services.alarms import AlarmLevel, alarm_payload, evaluate
from app.services.mqtt import MqttPublisher

logger = getLogger(__name__)

TICK_SECONDS = 1.0
RECONNECT_SECONDS = 5.0


def _metrics_topic() -> str:
    return f"{settings.MQTT_BASE_TOPIC}/reactor/metrics"


def _alarm_topic(metric: str) -> str:
    return f"{settings.MQTT_BASE_TOPIC}/alarms/{metric}"


async def _sleep_or_stop(stop_event: asyncio.Event, timeout: float) -> None:
    """Sleep up to timeout, waking immediately if stop_event is set."""
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=max(timeout, 0.0))
    except TimeoutError:
        pass


async def _connect_with_retry(publisher: MqttPublisher, stop_event: asyncio.Event) -> bool:
    """Connect, retrying every RECONNECT_SECONDS. False if stopped first."""
    while not stop_event.is_set():
        try:
            await publisher.connect()
            return True
        except aiomqtt.MqttError as exc:
            logger.warning("MQTT connect failed: %s; retrying in %ss", exc, RECONNECT_SECONDS)
            await _sleep_or_stop(stop_event, RECONNECT_SECONDS)
    return False


async def _publish_tick(publisher: MqttPublisher, last_levels: dict[str, AlarmLevel]) -> dict[str, AlarmLevel]:
    """Compute metrics, publish blob + changed alarms. Returns new levels."""
    with Session(engine) as session:
        metrics = get_reactor_metrics(session)

    await publisher.publish(_metrics_topic(), metrics)

    levels = evaluate(metrics)
    for metric, level in levels.items():
        if last_levels.get(metric) != level:
            await publisher.publish(
                _alarm_topic(metric),
                alarm_payload(metric, level, metrics[metric]),
                retain=True,
            )
    return levels


async def run_publisher_loop(stop_event: asyncio.Event) -> None:
    """Publish metrics + alarms at ~1Hz until stop_event is set."""
    publisher = MqttPublisher()
    if not await _connect_with_retry(publisher, stop_event):
        return

    last_levels: dict[str, AlarmLevel] = {}
    next_tick = time.monotonic()
    try:
        while not stop_event.is_set():
            try:
                last_levels = await _publish_tick(publisher, last_levels)
            except aiomqtt.MqttError as exc:
                logger.warning("MQTT publish failed: %s; reconnecting", exc)
                await publisher.disconnect()
                last_levels = {}  # force alarm re-publish after reconnect
                if not await _connect_with_retry(publisher, stop_event):
                    return
                continue
            except Exception:
                logger.exception("telemetry publish tick failed")

            next_tick += TICK_SECONDS
            await _sleep_or_stop(stop_event, next_tick - time.monotonic())
            if time.monotonic() - next_tick > TICK_SECONDS:
                next_tick = time.monotonic()  # fell behind; resync cadence
    finally:
        await publisher.disconnect()
