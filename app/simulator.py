"""Singleton plant simulator process (Phase 3, docs/roadmap.md).

Run with ``python -m app.simulator`` (own compose service, same image as the
API). Each 1Hz tick: derive targets from the current actuator setpoints
(Phase 4; super_admin publishes them, this process subscribes), integrate the
true plant state (services/plant_model.py), sample sensors (services/sensors.py),
persist the snapshot to the single plant_states row, then publish measured
telemetry — full blob to ``snrub/reactor/metrics``, per-metric readings to
``snrub/reactor/{group}/{metric}`` and retained ``snrub/alarms/{metric}`` on
level change. Singleton by construction (one compose service, replicas: 1);
request handlers stay stateless and read the latest snapshot.
"""

import asyncio
import contextlib
import json
import logging
import random
import signal
import time
from datetime import UTC, datetime
from logging import getLogger

import aiomqtt
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlmodel import Session, select

from app.core.config import settings
from app.db.database import engine
from app.models.plant_state import PlantState, measured_dict, true_state_dict
from app.services import incident_emitter, plant_model, sensors
from app.services.alarms import AlarmLevel, alarm_payload, evaluate
from app.services.mqtt import MqttPublisher

logger = getLogger(__name__)

TICK_SECONDS = 1.0
RECONNECT_SECONDS = 5.0
DB_RETRY_SECONDS = 2.0

# Grouped per-metric telemetry topics (docs/mqtt-telemetry.md). Payloads carry
# the canonical metric key so consumers never parse topics. Extract to a shared
# module in Phase 5 when the interlock subscribes.
METRIC_TOPIC_PATHS: dict[str, str] = {
    "reactor_power": "core/power",
    "core_temperature": "core/temperature",
    "reactivity": "core/reactivity",
    "coolant_flow_rate": "coolant/flow",
    "coolant_pressure": "coolant/pressure",
    "radiation_level": "radiation/level",
    "containment_integrity": "containment/integrity",
}


def _metrics_topic() -> str:
    return f"{settings.MQTT_BASE_TOPIC}/reactor/metrics"


def _metric_topic(metric: str) -> str:
    return f"{settings.MQTT_BASE_TOPIC}/reactor/{METRIC_TOPIC_PATHS[metric]}"


def _alarm_topic(metric: str) -> str:
    return f"{settings.MQTT_BASE_TOPIC}/alarms/{metric}"


def _actuators_topic() -> str:
    """Wildcard the API publishes actuator setpoints under (retained, one per actuator)."""
    return f"{settings.MQTT_BASE_TOPIC}/plant/actuators/#"


def _apply_actuator_message(actuator_state: dict[str, float], payload: bytes | str) -> None:
    """Fold one actuator setpoint message into actuator_state.

    Payload shape is set by controllers.actuators.set_actuator
    ({"actuator": name, "value": float, ...}). Values are clamped to
    ACTUATOR_RANGES (0–100). Malformed messages and unknown actuators are
    logged and ignored so a bad publish can't crash the tick loop.
    """
    try:
        data = json.loads(payload)
        name = data["actuator"]
        value = float(data["value"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        logger.warning("ignoring malformed actuator message: %r", payload)
        return
    if name not in plant_model.ACTUATOR_NOMINAL:
        logger.warning("ignoring unknown actuator %r", name)
        return
    low, high = plant_model.ACTUATOR_RANGES[name]
    clamped = max(low, min(high, value))
    if clamped != value:
        logger.warning("clamping actuator %s from %s to %s", name, value, clamped)
    actuator_state[name] = clamped


async def _consume_actuators(
    publisher: MqttPublisher, actuator_state: dict[str, float], stop_event: asyncio.Event
) -> None:
    """Background task: fold retained/live actuator messages into actuator_state."""
    async for message in publisher.messages:
        _apply_actuator_message(actuator_state, message.payload)
        if stop_event.is_set():
            return


async def _start_actuator_consumer(
    publisher: MqttPublisher, actuator_state: dict[str, float], stop_event: asyncio.Event
) -> asyncio.Task:
    """Subscribe to the actuator tree and spawn the consumer task."""
    await publisher.subscribe(_actuators_topic())
    return asyncio.create_task(_consume_actuators(publisher, actuator_state, stop_event))


async def _cancel_task(task: asyncio.Task) -> None:
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task


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


async def _wait_for_db(stop_event: asyncio.Event) -> bool:
    """Wait until the DB is up and migrated (the api service owns migrations)."""
    while not stop_event.is_set():
        try:
            with Session(engine) as session:
                session.exec(select(PlantState).limit(1)).first()
            return True
        except (OperationalError, ProgrammingError) as exc:
            logger.warning("Database not ready (%s); retrying in %ss", exc.__class__.__name__, DB_RETRY_SECONDS)
            await _sleep_or_stop(stop_event, DB_RETRY_SECONDS)
    return False


def _load_or_init_state() -> tuple[dict[str, float], dict[str, float], int]:
    """Resume from the persisted snapshot, or create it at base values."""
    with Session(engine) as session:
        row = session.exec(select(PlantState).order_by(PlantState.updated.desc())).first()
        if row is not None:
            logger.info("Resuming plant state at tick %s", row.tick)
            return true_state_dict(row), measured_dict(row), row.tick
        state = plant_model.initial_state()
        row = PlantState(
            **{f"true_{metric}": value for metric, value in state.items()},
            **{f"measured_{metric}": value for metric, value in state.items()},
        )
        session.add(row)
        session.commit()
        logger.info("Initialised plant state at base values")
        return state, dict(state), 0


def _persist(session: Session, state: dict[str, float], readings: dict[str, float], tick: int) -> None:
    row = session.exec(select(PlantState).order_by(PlantState.updated.desc())).first()
    if row is None:  # self-heal if the row was deleted externally
        row = PlantState(
            **{f"true_{metric}": value for metric, value in state.items()},
            **{f"measured_{metric}": value for metric, value in readings.items()},
        )
    else:
        for metric, value in state.items():
            setattr(row, f"true_{metric}", value)
        for metric, value in readings.items():
            setattr(row, f"measured_{metric}", value)
    row.tick = tick
    row.updated = datetime.utcnow()
    session.add(row)
    session.commit()


def _advance_plant(
    state: dict[str, float],
    prev_readings: dict[str, float],
    tick: int,
    rng: random.Random,
    actuator_state: dict[str, float],
    excursion_streaks: dict[str, int],
) -> tuple[dict[str, float], dict[str, float]]:
    """Integrate one tick from the current actuator setpoints and persist the snapshot.

    Phase 4 inversion: actuators drive true state (was: active incidents).
    Incidents are emitted from DANGER excursions after the snapshot is saved.
    """
    with Session(engine) as session:
        targets = plant_model.targets_from_actuators(actuator_state)
        state = plant_model.step(state, targets, TICK_SECONDS)
        readings = sensors.sample_all(state, prev_readings, TICK_SECONDS, rng=rng)
        _persist(session, state, readings, tick)
        incident_emitter.emit(state, excursion_streaks, session)
    return state, readings


async def _publish_tick(
    publisher: MqttPublisher,
    readings: dict[str, float],
    last_levels: dict[str, AlarmLevel],
) -> dict[str, AlarmLevel]:
    """Publish blob + per-metric readings + changed alarms. Returns new levels."""
    await publisher.publish(_metrics_topic(), readings)

    ts = datetime.now(UTC).isoformat()
    for metric, value in readings.items():
        await publisher.publish(_metric_topic(metric), {"metric": metric, "value": value, "ts": ts})

    # Alarms evaluate the measured values: operators alarm on what they see.
    levels = evaluate(readings)
    for metric, level in levels.items():
        if last_levels.get(metric) != level:
            await publisher.publish(
                _alarm_topic(metric),
                alarm_payload(metric, level, readings[metric]),
                retain=True,
            )
    return levels


async def run_simulator(stop_event: asyncio.Event, rng: random.Random | None = None) -> None:
    """Tick the plant at ~1Hz until stop_event is set."""
    rng = rng or random.Random()
    if not await _wait_for_db(stop_event):
        return
    state, prev_readings, tick = _load_or_init_state()

    # Seeded from nominals so an empty broker (no retained setpoints yet) yields
    # exactly the base plant. The consumer folds in retained + live setpoints.
    actuator_state: dict[str, float] = dict(plant_model.ACTUATOR_NOMINAL)

    publisher = MqttPublisher()
    if not await _connect_with_retry(publisher, stop_event):
        return

    consumer = await _start_actuator_consumer(publisher, actuator_state, stop_event)

    last_levels: dict[str, AlarmLevel] = {}
    excursion_streaks: dict[str, int] = {}
    next_tick = time.monotonic()
    try:
        while not stop_event.is_set():
            try:
                tick += 1
                state, prev_readings = _advance_plant(
                    state, prev_readings, tick, rng, actuator_state, excursion_streaks
                )
                last_levels = await _publish_tick(publisher, prev_readings, last_levels)
            except aiomqtt.MqttError as exc:
                logger.warning("MQTT publish failed: %s; reconnecting", exc)
                await _cancel_task(consumer)
                await publisher.disconnect()
                last_levels = {}  # force alarm re-publish after reconnect
                if not await _connect_with_retry(publisher, stop_event):
                    return
                consumer = await _start_actuator_consumer(publisher, actuator_state, stop_event)
                continue
            except Exception:
                logger.exception("simulator tick failed")

            next_tick += TICK_SECONDS
            await _sleep_or_stop(stop_event, next_tick - time.monotonic())
            if time.monotonic() - next_tick > TICK_SECONDS:
                next_tick = time.monotonic()  # fell behind; resync cadence
    finally:
        await _cancel_task(consumer)
        await publisher.disconnect()


async def _main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)
    logger.info("Plant simulator starting (tick %ss)", TICK_SECONDS)
    await run_simulator(stop_event)
    logger.info("Plant simulator stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    asyncio.run(_main())


if __name__ == "__main__":
    main()
