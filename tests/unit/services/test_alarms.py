import pytest

from app.services.alarms import AlarmLevel, alarm_payload, classify, evaluate
from app.services.setpoints import SETPOINTS


class TestClassifyHighSide:
    """Metrics that fail high: core_temperature (warn 900, danger 1000)."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (700, AlarmLevel.NORMAL),
            (899.9, AlarmLevel.NORMAL),
            (900, AlarmLevel.WARNING),  # at warning edge -> warning
            (999.9, AlarmLevel.WARNING),
            (1000, AlarmLevel.DANGER),  # at danger edge -> danger
            (1200, AlarmLevel.DANGER),
        ],
    )
    def test_core_temperature(self, value, expected):
        assert classify(value, SETPOINTS["core_temperature"]) == expected

    def test_reactor_power_edges(self):
        sp = SETPOINTS["reactor_power"]
        assert classify(95, sp) == AlarmLevel.NORMAL
        assert classify(100, sp) == AlarmLevel.WARNING
        assert classify(110, sp) == AlarmLevel.DANGER

    def test_reactivity_edges(self):
        sp = SETPOINTS["reactivity"]
        assert classify(0, sp) == AlarmLevel.NORMAL
        assert classify(1, sp) == AlarmLevel.WARNING
        assert classify(3, sp) == AlarmLevel.DANGER

    def test_radiation_level_edges(self):
        sp = SETPOINTS["radiation_level"]
        assert classify(2, sp) == AlarmLevel.NORMAL
        assert classify(5, sp) == AlarmLevel.WARNING
        assert classify(50, sp) == AlarmLevel.DANGER


class TestClassifyLowSide:
    """Metrics that fail low: coolant_flow_rate (warn 70, danger 50)."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (80, AlarmLevel.NORMAL),
            (70.1, AlarmLevel.NORMAL),
            (70, AlarmLevel.WARNING),  # at warning edge -> warning
            (50.1, AlarmLevel.WARNING),
            (50, AlarmLevel.DANGER),  # at danger edge -> danger
            (10, AlarmLevel.DANGER),
        ],
    )
    def test_coolant_flow_rate(self, value, expected):
        assert classify(value, SETPOINTS["coolant_flow_rate"]) == expected

    def test_containment_integrity_edges(self):
        sp = SETPOINTS["containment_integrity"]
        assert classify(100, sp) == AlarmLevel.NORMAL
        assert classify(95, sp) == AlarmLevel.WARNING
        assert classify(85, sp) == AlarmLevel.DANGER


class TestClassifyTwoSided:
    """coolant_pressure fails both ways: danger <100 / >180, warning 100-120 / 160-180."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (140, AlarmLevel.NORMAL),
            (120, AlarmLevel.WARNING),  # low warning edge
            (160, AlarmLevel.WARNING),  # high warning edge
            (100, AlarmLevel.DANGER),  # low danger edge
            (180, AlarmLevel.DANGER),  # high danger edge
            (90, AlarmLevel.DANGER),
            (200, AlarmLevel.DANGER),
        ],
    )
    def test_coolant_pressure(self, value, expected):
        assert classify(value, SETPOINTS["coolant_pressure"]) == expected


class TestEvaluate:
    def test_all_normal_baseline(self):
        metrics = {
            "reactor_power": 95.0,
            "core_temperature": 700.0,
            "reactivity": 0.0,
            "coolant_flow_rate": 80.0,
            "coolant_pressure": 140.0,
            "radiation_level": 2.0,
            "containment_integrity": 98.0,
        }
        assert evaluate(metrics) == dict.fromkeys(metrics, AlarmLevel.NORMAL)

    def test_mixed_levels(self):
        metrics = {
            "core_temperature": 1050.0,  # danger
            "coolant_flow_rate": 60.0,  # warning
            "radiation_level": 1.0,  # normal
        }
        levels = evaluate(metrics)
        assert levels["core_temperature"] == AlarmLevel.DANGER
        assert levels["coolant_flow_rate"] == AlarmLevel.WARNING
        assert levels["radiation_level"] == AlarmLevel.NORMAL

    def test_metrics_without_setpoint_are_skipped(self):
        levels = evaluate({"operator_alertness": 10.0, "core_temperature": 700.0})
        assert "operator_alertness" not in levels
        assert levels == {"core_temperature": AlarmLevel.NORMAL}

    def test_empty_metrics_returns_empty(self):
        assert evaluate({}) == {}


class TestAlarmPayload:
    def test_payload_shape(self):
        payload = alarm_payload("core_temperature", AlarmLevel.DANGER, 1050.0)
        assert payload["metric"] == "core_temperature"
        assert payload["level"] == "danger"
        assert payload["value"] == 1050.0
        assert isinstance(payload["ts"], str) and payload["ts"]
