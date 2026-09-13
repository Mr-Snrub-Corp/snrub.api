import asyncio
import json
import random
from unittest.mock import patch

import aiomqtt
import pytest

from app.core.config import settings
from app.services import plant_model, sensors
from app.services.alarms import AlarmLevel
from app.services.telemetry import BASE_METRICS
from app.simulator import (
    METRIC_TOPIC_PATHS,
    TICK_SECONDS,
    _actuators_topic,
    _advance_plant,
    _alarm_topic,
    _apply_actuator_message,
    _connect_with_retry,
    _consume_actuators,
    _metric_topic,
    _metrics_topic,
    _publish_tick,
    _sleep_or_stop,
    run_simulator,
)


class FakeMessage:
    """Stand-in for aiomqtt.Message; only payload is read by the consumer."""

    def __init__(self, payload):
        self.payload = payload


class FakePublisher:
    """Records MQTT calls. Optionally fails connect/publish."""

    def __init__(self):
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.published: list[dict] = []
        self.subscribed: list[str] = []
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

    async def subscribe(self, topic, *, qos=0):
        self.subscribed.append(topic)

    @property
    def messages(self):
        return self._messages()

    async def _messages(self):
        # No actuator messages in these unit tests; block until cancelled so the
        # consumer task behaves like the real never-ending iterator.
        await asyncio.Event().wait()
        yield  # pragma: no cover - unreachable, keeps this an async generator


class DummySession:
    def __init__(self, _engine):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


NORMAL_READINGS = {
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


async def _db_ready(stop_event):
    return True


class TestTopics:
    def test_metrics_topic(self):
        assert _metrics_topic() == f"{settings.MQTT_BASE_TOPIC}/reactor/metrics"

    def test_metric_topics_are_grouped(self):
        assert _metric_topic("core_temperature") == f"{settings.MQTT_BASE_TOPIC}/reactor/core/temperature"
        assert _metric_topic("coolant_flow_rate") == f"{settings.MQTT_BASE_TOPIC}/reactor/coolant/flow"

    def test_topic_paths_cover_exactly_the_canonical_metrics(self):
        assert set(METRIC_TOPIC_PATHS) == set(plant_model.METRICS)

    def test_alarm_topic_stays_flat_canonical(self):
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

        with patch("app.simulator.RECONNECT_SECONDS", 0):
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

        with patch("app.simulator.RECONNECT_SECONDS", 0):
            assert _run(_connect_with_retry(publisher, stop)) is False


class TestAdvancePlant:
    def test_nominal_actuators_keep_plant_quiescent(self):
        persisted = {}

        def fake_persist(session, state, readings, tick):
            persisted.update(state=state, readings=readings, tick=tick)

        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        with (
            patch("app.simulator.Session", DummySession),
            patch("app.simulator._persist", fake_persist),
            patch("app.simulator.incident_emitter.emit"),
        ):
            state, readings = _advance_plant(
                plant_model.initial_state(),
                dict(BASE_METRICS),
                7,
                random.Random(3),
                actuator_state,
                {},
            )

        # Nominal actuators map to the base targets, so state stays quiescent.
        expected_state = plant_model.step(plant_model.initial_state(), dict(BASE_METRICS), TICK_SECONDS)
        expected_readings = sensors.sample_all(expected_state, dict(BASE_METRICS), TICK_SECONDS, rng=random.Random(3))
        assert state == expected_state
        assert readings == expected_readings
        assert persisted["state"] == state
        assert persisted["readings"] == readings
        assert persisted["tick"] == 7

    def test_actuators_drive_targets_not_incidents(self):
        """Phase 4: a lowered pump commands less coolant flow; incidents no longer feed targets."""
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        actuator_state["pump_speed"] = 20.0

        with (
            patch("app.simulator.Session", DummySession),
            patch("app.simulator._persist", lambda *a, **k: None),
            patch("app.simulator.incident_emitter.emit"),
        ):
            state, _ = _advance_plant(
                plant_model.initial_state(),
                dict(BASE_METRICS),
                1,
                random.Random(3),
                actuator_state,
                {},
            )

        expected_targets = plant_model.targets_from_actuators(actuator_state)
        expected_state = plant_model.step(plant_model.initial_state(), expected_targets, TICK_SECONDS)
        assert state == expected_state
        # pump_speed 20 (< nominal 80) commands the coolant-flow target down.
        assert state["coolant_flow_rate"] < BASE_METRICS["coolant_flow_rate"]


class TestActuatorConsumption:
    def test_actuators_topic_is_the_retained_wildcard(self):
        assert _actuators_topic() == f"{settings.MQTT_BASE_TOPIC}/plant/actuators/#"

    def test_apply_message_updates_named_actuator(self):
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        _apply_actuator_message(actuator_state, json.dumps({"actuator": "pump_speed", "value": 20.0}))
        assert actuator_state["pump_speed"] == 20.0

    def test_apply_message_accepts_bytes_payload(self):
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        _apply_actuator_message(actuator_state, json.dumps({"actuator": "leak_rate", "value": 55}).encode())
        assert actuator_state["leak_rate"] == 55.0

    def test_apply_message_clamps_out_of_range_value(self):
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        _apply_actuator_message(actuator_state, json.dumps({"actuator": "leak_rate", "value": 999}))
        assert actuator_state["leak_rate"] == 100.0
        _apply_actuator_message(actuator_state, json.dumps({"actuator": "pump_speed", "value": -5}))
        assert actuator_state["pump_speed"] == 0.0

    def test_apply_message_ignores_unknown_actuator(self):
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        _apply_actuator_message(actuator_state, json.dumps({"actuator": "not_real", "value": 10}))
        assert "not_real" not in actuator_state
        assert actuator_state == plant_model.ACTUATOR_NOMINAL

    @pytest.mark.parametrize("bad", ["not json", json.dumps({"actuator": "pump_speed"}), json.dumps({"value": 5})])
    def test_apply_message_ignores_malformed(self, bad):
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        _apply_actuator_message(actuator_state, bad)
        assert actuator_state == plant_model.ACTUATOR_NOMINAL

    def test_consumer_folds_messages_into_state(self):
        actuator_state = dict(plant_model.ACTUATOR_NOMINAL)
        stop = asyncio.Event()

        class OnePublisher:
            @property
            def messages(self):
                return self._gen()

            async def _gen(self):
                yield FakeMessage(json.dumps({"actuator": "xenon_injection", "value": 80.0}))

        _run(_consume_actuators(OnePublisher(), actuator_state, stop))
        assert actuator_state["xenon_injection"] == 80.0


class TestPublishTick:
    def test_publishes_blob_then_per_metric_then_changed_alarms(self):
        publisher = FakePublisher()
        # Measured danger while the (unseen) true value could be normal:
        # alarms act on what operators see.
        readings = {**NORMAL_READINGS, "core_temperature": 1050.0}

        levels = _run(_publish_tick(publisher, readings, {}))

        assert levels["core_temperature"] == AlarmLevel.DANGER
        assert publisher.published[0]["topic"] == _metrics_topic()
        assert publisher.published[0]["payload"] == readings
        assert publisher.published[0]["retain"] is False

        per_metric = publisher.published[1 : 1 + len(readings)]
        assert {item["topic"] for item in per_metric} == {_metric_topic(metric) for metric in readings}
        temp_item = next(item for item in per_metric if item["topic"] == _metric_topic("core_temperature"))
        assert temp_item["payload"]["metric"] == "core_temperature"
        assert temp_item["payload"]["value"] == 1050.0
        assert "ts" in temp_item["payload"]

        alarms = publisher.published[1 + len(readings) :]
        danger = next(item for item in alarms if item["topic"] == _alarm_topic("core_temperature"))
        assert danger["retain"] is True
        assert danger["payload"]["level"] == "danger"
        assert danger["payload"]["value"] == 1050.0

    def test_skips_alarms_whose_level_has_not_changed(self):
        publisher = FakePublisher()
        last_levels = dict.fromkeys(NORMAL_READINGS, AlarmLevel.NORMAL)

        levels = _run(_publish_tick(publisher, NORMAL_READINGS, last_levels))

        assert levels == last_levels
        assert len(publisher.published) == 1 + len(NORMAL_READINGS)  # blob + per-metric, no alarms


class TestRunSimulator:
    def test_returns_immediately_when_stop_set_before_start(self):
        stop = asyncio.Event()
        stop.set()
        fake = FakePublisher()

        with patch("app.simulator.MqttPublisher", return_value=fake):
            _run(run_simulator(stop))

        assert fake.connect_calls == 0
        assert fake.disconnect_calls == 0

    def test_ticks_then_stops(self):
        stop = asyncio.Event()
        fake = FakePublisher()
        ticks = {"n": 0}

        async def one_tick(publisher, readings, last_levels):
            ticks["n"] += 1
            stop.set()
            return dict.fromkeys(NORMAL_READINGS, AlarmLevel.NORMAL)

        with (
            patch("app.simulator.MqttPublisher", return_value=fake),
            patch("app.simulator._wait_for_db", _db_ready),
            patch("app.simulator._load_or_init_state", return_value=(dict(BASE_METRICS), dict(BASE_METRICS), 0)),
            patch(
                "app.simulator._advance_plant",
                lambda state, prev, tick, rng, actuators, streaks: (state, prev),
            ),
            patch("app.simulator._publish_tick", side_effect=one_tick),
            patch("app.simulator.TICK_SECONDS", 0),
        ):
            _run(run_simulator(stop))

        assert ticks["n"] == 1
        assert fake.connect_calls == 1
        assert fake.disconnect_calls == 1

    def test_reconnects_after_publish_mqtt_error(self):
        stop = asyncio.Event()
        fake = FakePublisher()
        ticks = {"n": 0}

        async def fail_then_ok(publisher, readings, last_levels):
            ticks["n"] += 1
            if ticks["n"] == 1:
                raise aiomqtt.MqttError("broker gone")
            stop.set()
            return {}

        with (
            patch("app.simulator.MqttPublisher", return_value=fake),
            patch("app.simulator._wait_for_db", _db_ready),
            patch("app.simulator._load_or_init_state", return_value=(dict(BASE_METRICS), dict(BASE_METRICS), 0)),
            patch(
                "app.simulator._advance_plant",
                lambda state, prev, tick, rng, actuators, streaks: (state, prev),
            ),
            patch("app.simulator._publish_tick", side_effect=fail_then_ok),
            patch("app.simulator.TICK_SECONDS", 0),
            patch("app.simulator.RECONNECT_SECONDS", 0),
        ):
            _run(run_simulator(stop))

        assert ticks["n"] == 2
        assert fake.disconnect_calls >= 2  # once on error, once in finally
        assert fake.connect_calls == 2

    def test_continues_after_non_mqtt_tick_error(self):
        stop = asyncio.Event()
        fake = FakePublisher()
        ticks = {"n": 0}

        async def boom_then_ok(publisher, readings, last_levels):
            ticks["n"] += 1
            if ticks["n"] == 1:
                raise RuntimeError("compute failed")
            stop.set()
            return {}

        with (
            patch("app.simulator.MqttPublisher", return_value=fake),
            patch("app.simulator._wait_for_db", _db_ready),
            patch("app.simulator._load_or_init_state", return_value=(dict(BASE_METRICS), dict(BASE_METRICS), 0)),
            patch(
                "app.simulator._advance_plant",
                lambda state, prev, tick, rng, actuators, streaks: (state, prev),
            ),
            patch("app.simulator._publish_tick", side_effect=boom_then_ok),
            patch("app.simulator.TICK_SECONDS", 0),
        ):
            _run(run_simulator(stop))

        assert ticks["n"] == 2
        assert fake.disconnect_calls == 1

    def test_stops_during_reconnect_after_mqtt_error(self):
        stop = asyncio.Event()
        fake = FakePublisher()

        async def fail_and_stop(publisher, readings, last_levels):
            stop.set()
            raise aiomqtt.MqttError("broker gone")

        with (
            patch("app.simulator.MqttPublisher", return_value=fake),
            patch("app.simulator._wait_for_db", _db_ready),
            patch("app.simulator._load_or_init_state", return_value=(dict(BASE_METRICS), dict(BASE_METRICS), 0)),
            patch(
                "app.simulator._advance_plant",
                lambda state, prev, tick, rng, actuators, streaks: (state, prev),
            ),
            patch("app.simulator._publish_tick", side_effect=fail_and_stop),
            patch("app.simulator.RECONNECT_SECONDS", 0),
        ):
            _run(run_simulator(stop))

        assert fake.disconnect_calls == 2  # error path + finally


@pytest.mark.skip(reason="TODO: implement later")
def test_run_simulator_resyncs_cadence_when_tick_falls_behind():
    """When a tick overruns TICK_SECONDS, next_tick is reset to monotonic() rather than drifting."""


@pytest.mark.skip(reason="TODO: implement later")
def test_publish_tick_skips_metrics_without_setpoints():
    """Metrics not in SETPOINTS must not produce snrub/alarms/{metric} messages."""
