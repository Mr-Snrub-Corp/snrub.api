from unittest.mock import Mock

import pytest

from app.models.incident_report import IncidentStatus
from app.services.telemetry import (
    BASE_CONTAINMENT_INTEGRITY,
    BASE_COOLANT_FLOW_RATE,
    BASE_COOLANT_PRESSURE,
    BASE_CORE_TEMPERATURE,
    BASE_RADIATION_LEVEL,
    BASE_REACTIVITY,
    BASE_REACTOR_POWER_OUTPUT,
    INCIDENT_IMPACT_MAP,
    STATUS_WEIGHT,
    apply_impact,
    noise,
)


def _base_metrics() -> dict[str, float]:
    return {
        "reactor_power": float(BASE_REACTOR_POWER_OUTPUT),
        "core_temperature": float(BASE_CORE_TEMPERATURE),
        "reactivity": float(BASE_REACTIVITY),
        "coolant_flow_rate": float(BASE_COOLANT_FLOW_RATE),
        "coolant_pressure": float(BASE_COOLANT_PRESSURE),
        "radiation_level": float(BASE_RADIATION_LEVEL),
        "containment_integrity": float(BASE_CONTAINMENT_INTEGRITY),
    }


def _rng_returning(*values: float) -> Mock:
    rng = Mock()
    rng.uniform.side_effect = list(values)
    return rng


class TestNoise:
    def test_non_zero_value_is_multiplied(self):
        rng = _rng_returning(1.002)
        result = noise({"reactor_power": 100.0}, rng=rng)

        assert result["reactor_power"] == pytest.approx(100.0 * 1.002)
        rng.uniform.assert_called_once_with(0.995, 1.005)

    def test_zero_value_gets_half_width_additive_jitter(self):
        rng = _rng_returning(0.002)
        result = noise({"reactivity": 0.0}, rng=rng)

        assert result["reactivity"] == pytest.approx(0.002)
        rng.uniform.assert_called_once_with(-0.0025, 0.0025)

    def test_zero_value_additive_jitter_can_be_negative(self):
        rng = _rng_returning(-0.002)
        result = noise({"reactivity": 0.0}, rng=rng)

        assert result["reactivity"] == pytest.approx(-0.002)

    def test_all_input_keys_present_in_output(self):
        data = {"reactor_power": 95.0, "core_temperature": 700.0, "reactivity": 0.0}

        result = noise(data, rng=_rng_returning(1.001, 1.001, 0.001))

        assert set(result.keys()) == set(data.keys())

    def test_no_extra_keys_in_output(self):
        data = {"reactor_power": 95.0}

        result = noise(data, rng=_rng_returning(1.001))

        assert list(result.keys()) == ["reactor_power"]

    def test_original_dict_is_not_mutated(self):
        data = {"reactor_power": 95.0, "reactivity": 0.0}
        original = dict(data)

        noise(data, rng=_rng_returning(1.001, 0.001))

        assert data == original

    def test_empty_dict_returns_empty_dict(self):
        assert noise({}, rng=_rng_returning()) == {}


class TestApplyImpact:
    def test_confirmed_applies_full_deltas_for_multi_metric_incident(self):
        data = _base_metrics()

        result = apply_impact(data, "primary_coolant_loss", IncidentStatus.CONFIRMED)

        assert result["coolant_flow_rate"] == pytest.approx(60.0)
        assert result["core_temperature"] == pytest.approx(850.0)
        assert result["reactor_power"] == pytest.approx(BASE_REACTOR_POWER_OUTPUT)

    @pytest.mark.parametrize(
        ("status", "expected_flow", "expected_temp"),
        [
            (IncidentStatus.REPORTED, 74.0, 745.0),
            (IncidentStatus.UNDER_REVIEW, 68.0, 790.0),
            (IncidentStatus.CONFIRMED, 60.0, 850.0),
            (IncidentStatus.MITIGATION_IN_PROGRESS, 70.0, 775.0),
            (IncidentStatus.CONTAINED, 76.0, 730.0),
        ],
    )
    def test_status_weight_scales_deltas(self, status, expected_flow, expected_temp):
        data = _base_metrics()
        weight = STATUS_WEIGHT[status]
        deltas = INCIDENT_IMPACT_MAP["primary_coolant_loss"]

        result = apply_impact(data, "primary_coolant_loss", status)

        assert result["coolant_flow_rate"] == pytest.approx(
            BASE_COOLANT_FLOW_RATE + deltas["coolant_flow_rate"] * weight
        )
        assert result["core_temperature"] == pytest.approx(BASE_CORE_TEMPERATURE + deltas["core_temperature"] * weight)

    @pytest.mark.parametrize(
        "status",
        [
            IncidentStatus.RESOLVED,
            IncidentStatus.CLOSED,
            IncidentStatus.FALSE_ALARM,
        ],
    )
    def test_zero_weight_status_leaves_metrics_unchanged(self, status):
        data = _base_metrics()

        result = apply_impact(data, "primary_coolant_loss", status)

        assert result == data

    def test_unknown_incident_type_returns_unchanged_copy(self):
        data = _base_metrics()

        result = apply_impact(data, "operator_asleep_at_station", IncidentStatus.CONFIRMED)

        assert result == data
        assert result is not data

    def test_sequential_calls_stack_deltas(self):
        data = _base_metrics()

        once = apply_impact(data, "primary_coolant_loss", IncidentStatus.CONFIRMED)
        twice = apply_impact(once, "primary_coolant_loss", IncidentStatus.CONFIRMED)

        assert twice["coolant_flow_rate"] == pytest.approx(40.0)
        assert twice["core_temperature"] == pytest.approx(1000.0)

    def test_only_affected_metrics_change(self):
        data = _base_metrics()

        result = apply_impact(data, "xenon_poisoning_instability", IncidentStatus.CONFIRMED)

        assert result["reactivity"] == pytest.approx(-3.0)
        assert result["reactor_power"] == pytest.approx(BASE_REACTOR_POWER_OUTPUT)
        assert result["coolant_flow_rate"] == pytest.approx(BASE_COOLANT_FLOW_RATE)

    def test_input_dict_is_not_mutated(self):
        data = _base_metrics()
        original = dict(data)

        apply_impact(data, "coolant_pump_failure", IncidentStatus.CONFIRMED)

        assert data == original
