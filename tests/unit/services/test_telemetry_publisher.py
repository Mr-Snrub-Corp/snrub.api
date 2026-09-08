import asyncio
from unittest.mock import patch

import aiomqtt
import pytest

from app.core.config import settings
from app.services.alarms import AlarmLevel
from app.services.telemetry_publisher import (
    _alarm_topic,
    _connect_with_retry,
    _metrics_topic,
    _publish_tick,
    _sleep_or_stop,
    run_publisher_loop,
)


class FakePublisher:
    """Records MQTT calls. Optionally fails connect/publish."""

    def __init__(self):
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.published: list[dict] = []
        self.connect_error: BaseException | None = None
        self.publish_error: BaseException | None = None
        self._connect_errors: list[BaseException] = []

    async def connect(self):
        self.connect_calls += 1
        if self._connect_errors:
            raise self._connect_errors.pop(0)
        if self.connect_error is not None:
            raise self.connect_error

    async def disconnect(self):
        self.disconnect_calls += 1

    async def publish(self, topic, payload, *, retain=False, qos=0):
        if self.publish_error is not None:
            raise self.publish_error
        self.published.append({"topic": topic, "payload": payload, "retain": retain, "qos": qos})


class DummySession:
    def __init__(self, _engine):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


NORMAL_METRICS = {
    "reactor_power": 95.0,
    "core_temperature": 700.0,
    "reactivity": 0.0,
    "coolant_flow_rate": 80.0,
    "coolant_pressure": 140.0,
    "radiation_level": 2.0,
    "containment_integrity": 98.0,
}


def _run(coro):
    return asyncio.run(coro)


class TestTopics:
    def test_metrics_topic(self):
        assert _metrics_topic() == f"{settings.MQTT_BASE_TOPIC}/reactor/metrics"

    def test_alarm_topic(self):
        assert _alarm_topic("core_temperature") == f"{settings.MQTT_BASE_TOPIC}/alarms/core_temperature"


class TestSleepOrStop:
    def test_returns_after_timeout_when_stop_not_set(self):
        stop = asyncio.Event()
        _run(_sleep_or_stop(stop, 0.01))
        assert not stop.is_set()

    def test_returns_immediately_when_stop_already_set(self):
        stop = asyncio.Event()
        stop.set()
        _run(_sleep_or_stop(stop, 30.0))

    def test_negative_timeout_is_clamped_to_zero(self):
        stop = asyncio.Event()
        _run(_sleep_or_stop(stop, -1.0))


class TestConnectWithRetry:
    def test_returns_true_on_first_successful_connect(self):
        publisher = FakePublisher()
        stop = asyncio.Event()

        assert _run(_connect_with_retry(publisher, stop)) is True
        assert publisher.connect_calls == 1

    def test_retries_after_mqtt_error_then_succeeds(self):
        publisher = FakePublisher()
        publisher._connect_errors = [aiomqtt.MqttError("refused")]
        stop = asyncio.Event()

        with patch("app.services.telemetry_publisher.RECONNECT_SECONDS", 0):
            assert _run(_connect_with_retry(publisher, stop)) is True

        assert publisher.connect_calls == 2

    def test_returns_false_when_stopped_before_connect(self):
        publisher = FakePublisher()
        stop = asyncio.Event()
        stop.set()

        assert _run(_connect_with_retry(publisher, stop)) is False
        assert publisher.connect_calls == 0

    def test_returns_false_when_stopped_during_retry_wait(self):
        publisher = FakePublisher()
        stop = asyncio.Event()

        async def connect_and_stop():
            stop.set()
            raise aiomqtt.MqttError("refused")

        publisher.connect = connect_and_stop  # type: ignore[method-assign]

        with patch("app.services.telemetry_publisher.RECONNECT_SECONDS", 0):
            assert _run(_connect_with_retry(publisher, stop)) is False


class TestPublishTick:
    def test_publishes_metrics_blob_and_changed_alarms(self):
        publisher = FakePublisher()
        metrics = {**NORMAL_METRICS, "core_temperature": 1050.0}

        with (
            patch("app.services.telemetry_publisher.Session", DummySession),
            patch("app.services.telemetry_publisher.get_reactor_metrics", return_value=metrics),
        ):
            levels = _run(_publish_tick(publisher, {}))

        assert levels["core_temperature"] == AlarmLevel.DANGER
        assert publisher.published[0]["topic"] == _metrics_topic()
        assert publisher.published[0]["payload"] == metrics
        assert publisher.published[0]["retain"] is False

        alarm_topics = {item["topic"] for item in publisher.published[1:]}
        assert _alarm_topic("core_temperature") in alarm_topics
        danger = next(item for item in publisher.published if item["topic"] == _alarm_topic("core_temperature"))
        assert danger["retain"] is True
        assert danger["payload"]["level"] == "danger"
        assert danger["payload"]["value"] == 1050.0

    def test_skips_alarms_whose_level_has_not_changed(self):
        publisher = FakePublisher()
        last_levels = dict.fromkeys(NORMAL_METRICS, AlarmLevel.NORMAL)

        with (
            patch("app.services.telemetry_publisher.Session", DummySession),
            patch("app.services.telemetry_publisher.get_reactor_metrics", return_value=NORMAL_METRICS),
        ):
            levels = _run(_publish_tick(publisher, last_levels))

        assert levels == last_levels
        assert len(publisher.published) == 1
        assert publisher.published[0]["topic"] == _metrics_topic()


class TestRunPublisherLoop:
    def test_returns_immediately_when_stop_set_before_connect(self):
        stop = asyncio.Event()
        stop.set()
        fake = FakePublisher()

        with patch("app.services.telemetry_publisher.MqttPublisher", return_value=fake):
            _run(run_publisher_loop(stop))

        assert fake.connect_calls == 0
        assert fake.disconnect_calls == 0  # return is before the try/finally

    def test_publishes_then_stops(self):
        stop = asyncio.Event()
        fake = FakePublisher()
        ticks = {"n": 0}

        async def one_tick(publisher, last_levels):
            ticks["n"] += 1
            stop.set()
            return dict.fromkeys(NORMAL_METRICS, AlarmLevel.NORMAL)

        with (
            patch("app.services.telemetry_publisher.MqttPublisher", return_value=fake),
            patch("app.services.telemetry_publisher._publish_tick", side_effect=one_tick),
            patch("app.services.telemetry_publisher.TICK_SECONDS", 0),
        ):
            _run(run_publisher_loop(stop))

        assert ticks["n"] == 1
        assert fake.connect_calls == 1
        assert fake.disconnect_calls == 1

    def test_reconnects_after_publish_mqtt_error(self):
        stop = asyncio.Event()
        fake = FakePublisher()
        ticks = {"n": 0}

        async def fail_then_ok(publisher, last_levels):
            ticks["n"] += 1
            if ticks["n"] == 1:
                raise aiomqtt.MqttError("broker gone")
            stop.set()
            return {}

        with (
            patch("app.services.telemetry_publisher.MqttPublisher", return_value=fake),
            patch("app.services.telemetry_publisher._publish_tick", side_effect=fail_then_ok),
            patch("app.services.telemetry_publisher.TICK_SECONDS", 0),
            patch("app.services.telemetry_publisher.RECONNECT_SECONDS", 0),
        ):
            _run(run_publisher_loop(stop))

        assert ticks["n"] == 2
        assert fake.disconnect_calls >= 2  # once on error, once in finally
        assert fake.connect_calls == 2

    def test_continues_after_non_mqtt_tick_error(self):
        stop = asyncio.Event()
        fake = FakePublisher()
        ticks = {"n": 0}

        async def boom_then_ok(publisher, last_levels):
            ticks["n"] += 1
            if ticks["n"] == 1:
                raise RuntimeError("compute failed")
            stop.set()
            return {}

        with (
            patch("app.services.telemetry_publisher.MqttPublisher", return_value=fake),
            patch("app.services.telemetry_publisher._publish_tick", side_effect=boom_then_ok),
            patch("app.services.telemetry_publisher.TICK_SECONDS", 0),
        ):
            _run(run_publisher_loop(stop))

        assert ticks["n"] == 2
        assert fake.disconnect_calls == 1

    def test_stops_during_reconnect_after_mqtt_error(self):
        stop = asyncio.Event()
        fake = FakePublisher()

        async def fail_and_stop(publisher, last_levels):
            stop.set()
            raise aiomqtt.MqttError("broker gone")

        with (
            patch("app.services.telemetry_publisher.MqttPublisher", return_value=fake),
            patch("app.services.telemetry_publisher._publish_tick", side_effect=fail_and_stop),
            patch("app.services.telemetry_publisher.RECONNECT_SECONDS", 0),
        ):
            _run(run_publisher_loop(stop))

        assert fake.disconnect_calls == 2  # error path + finally


@pytest.mark.skip(reason="TODO: implement later")
def test_run_publisher_loop_resyncs_cadence_when_tick_falls_behind():
    """When a tick overruns TICK_SECONDS, next_tick is reset to monotonic() rather than drifting."""


@pytest.mark.skip(reason="TODO: implement later")
def test_publish_tick_skips_metrics_without_setpoints():
    """Metrics not in SETPOINTS must not produce snrub/alarms/{metric} messages."""
