import pytest

from app.models.incident_report import IncidentReportTelemetry, IncidentStatus
from app.services.telemetry import (
    BASE_CONTAINMENT_INTEGRITY,
    BASE_COOLANT_FLOW_RATE,
    BASE_COOLANT_PRESSURE,
    BASE_CORE_TEMPERATURE,
    BASE_METRICS,
    BASE_RADIATION_LEVEL,
    BASE_REACTIVITY,
    BASE_REACTOR_POWER_OUTPUT,
    INCIDENT_IMPACT_MAP,
    STATUS_WEIGHT,
    apply_impact,
    compute_targets,
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


def _report(code: str, status: IncidentStatus) -> IncidentReportTelemetry:
    return IncidentReportTelemetry(incident_type_code=code, status=status)


class TestComputeTargets:
    def test_no_reports_returns_bases(self):
        assert compute_targets([]) == BASE_METRICS

    def test_confirmed_report_applies_full_deltas(self):
        result = compute_targets([_report("primary_coolant_loss", IncidentStatus.CONFIRMED)])

        assert result["coolant_flow_rate"] == pytest.approx(60.0)
        assert result["core_temperature"] == pytest.approx(850.0)
        assert result["reactor_power"] == pytest.approx(BASE_REACTOR_POWER_OUTPUT)

    def test_reports_stack(self):
        reports = [
            _report("primary_coolant_loss", IncidentStatus.CONFIRMED),
            _report("primary_coolant_loss", IncidentStatus.CONFIRMED),
        ]

        result = compute_targets(reports)

        assert result["coolant_flow_rate"] == pytest.approx(40.0)
        assert result["core_temperature"] == pytest.approx(1000.0)

    def test_untracked_code_is_ignored(self):
        result = compute_targets([_report("operator_asleep_at_station", IncidentStatus.CONFIRMED)])

        assert result == BASE_METRICS

    def test_deterministic_repeat_call_is_identical(self):
        reports = [_report("coolant_pump_failure", IncidentStatus.UNDER_REVIEW)]

        assert compute_targets(reports) == compute_targets(reports)


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
