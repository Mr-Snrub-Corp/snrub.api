from app.services.setpoints import SETPOINTS, Setpoint

# Metrics emitted by services/telemetry.compute_metrics.
METRIC_NAMES = {
    "reactor_power",
    "core_temperature",
    "reactivity",
    "coolant_flow_rate",
    "coolant_pressure",
    "radiation_level",
    "containment_integrity",
}


class TestSetpointCoverage:
    def test_every_computed_metric_has_a_setpoint(self):
        assert set(SETPOINTS.keys()) == METRIC_NAMES

    def test_no_unknown_metrics(self):
        assert set(SETPOINTS.keys()) <= METRIC_NAMES

    def test_key_matches_setpoint_metric_field(self):
        for key, setpoint in SETPOINTS.items():
            assert key == setpoint.metric


class TestSetpointOrdering:
    def test_high_side_danger_at_or_above_warning(self):
        for setpoint in SETPOINTS.values():
            if setpoint.warning_high is not None and setpoint.danger_high is not None:
                assert setpoint.danger_high >= setpoint.warning_high

    def test_low_side_danger_at_or_below_warning(self):
        for setpoint in SETPOINTS.values():
            if setpoint.warning_low is not None and setpoint.danger_low is not None:
                assert setpoint.danger_low <= setpoint.warning_low

    def test_each_setpoint_defines_at_least_one_threshold(self):
        for setpoint in SETPOINTS.values():
            thresholds = (setpoint.warning_low, setpoint.warning_high, setpoint.danger_low, setpoint.danger_high)
            assert any(t is not None for t in thresholds)


class TestSetpointIsFrozen:
    def test_setpoint_is_immutable(self):
        setpoint = Setpoint("x", danger_high=10)
        try:
            setpoint.danger_high = 20  # type: ignore[misc]
        except AttributeError:
            return
        raise AssertionError("Setpoint should be frozen")
