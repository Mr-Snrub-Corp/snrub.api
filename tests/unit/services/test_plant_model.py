from math import exp

import pytest

from app.services.plant_model import (
    K_CONTAINMENT_RADIATION,
    K_FLOW_TEMP,
    K_POWER_TEMP,
    K_REACTIVITY_POWER,
    K_TEMP_REACTIVITY,
    METRICS,
    PHYSICAL_RANGES,
    TAUS,
    initial_state,
    step,
)
from app.services.telemetry import BASE_METRICS


def _alpha(metric: str, dt: float = 1.0) -> float:
    return 1.0 - exp(-dt / TAUS[metric])


class TestRegistry:
    def test_knob_tables_cover_exactly_the_canonical_metrics(self):
        assert set(METRICS) == set(BASE_METRICS)
        assert set(TAUS) == set(METRICS)
        assert set(PHYSICAL_RANGES) == set(METRICS)

    def test_initial_state_is_bases(self):
        assert initial_state() == BASE_METRICS


class TestStep:
    def test_quiescent_state_is_fixed_point(self):
        state = initial_state()

        result = step(state, dict(BASE_METRICS), 1.0)

        assert result == BASE_METRICS

    def test_returns_all_metrics(self):
        result = step(initial_state(), dict(BASE_METRICS), 1.0)

        assert set(result.keys()) == set(METRICS)

    def test_single_metric_lerp_math(self):
        # coolant_pressure has no coupling terms: pure first-order lerp
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["coolant_pressure"] = 170.0

        result = step(state, targets, 1.0)

        expected = 130.0 + (170.0 - 130.0) * _alpha("coolant_pressure")
        assert result["coolant_pressure"] == pytest.approx(expected)

    def test_converges_to_target(self):
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["coolant_pressure"] = 170.0

        for _ in range(int(5 * TAUS["coolant_pressure"])):
            state = step(state, targets, 1.0)

        assert state["coolant_pressure"] == pytest.approx(170.0, rel=0.01)

    def test_no_overshoot_at_dt_1s(self):
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["coolant_pressure"] = 170.0
        previous = state["coolant_pressure"]

        for _ in range(120):
            state = step(state, targets, 1.0)
            assert previous <= state["coolant_pressure"] <= 170.0
            previous = state["coolant_pressure"]

    def test_no_overshoot_at_pathological_dt(self):
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["coolant_pressure"] = 170.0

        result = step(state, targets, 1000.0)

        assert 130.0 < result["coolant_pressure"] <= 170.0

    def test_clamps_to_physical_range_high(self):
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["radiation_level"] = 10_000.0

        result = step(state, targets, 1000.0)

        assert result["radiation_level"] == PHYSICAL_RANGES["radiation_level"][1]

    def test_clamps_to_physical_range_low(self):
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["containment_integrity"] = -10_000.0

        result = step(state, targets, 1000.0)

        assert result["containment_integrity"] == PHYSICAL_RANGES["containment_integrity"][0]

    def test_flow_deficit_raises_temperature_equilibrium(self):
        # Hold flow target at 60 (deficit of 20); the coupled equilibrium is
        # damped slightly below base + K_FLOW_TEMP*20 by the negative feedback
        # loop (gain K_TEMP_REACTIVITY * K_REACTIVITY_POWER * K_POWER_TEMP).
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["coolant_flow_rate"] = 60.0

        for _ in range(600):
            state = step(state, targets, 1.0)

        loop_gain = K_TEMP_REACTIVITY * K_REACTIVITY_POWER * K_POWER_TEMP
        expected_temp = BASE_METRICS["core_temperature"] + (K_FLOW_TEMP * 20.0) / (1.0 + loop_gain)
        assert state["coolant_flow_rate"] == pytest.approx(60.0, rel=0.01)
        assert state["core_temperature"] == pytest.approx(expected_temp, rel=1e-3)

    def test_reactivity_raises_power(self):
        state = initial_state()
        state["reactivity"] = 2.0

        result = step(state, dict(BASE_METRICS), 1.0)

        expected = 95.0 + (K_REACTIVITY_POWER * 2.0) * _alpha("reactor_power")
        assert result["reactor_power"] == pytest.approx(expected)

    def test_containment_loss_raises_radiation(self):
        state = initial_state()
        state["containment_integrity"] = 85.0

        result = step(state, dict(BASE_METRICS), 1.0)

        expected = 2.0 + (K_CONTAINMENT_RADIATION * 10.0) * _alpha("radiation_level")
        assert result["radiation_level"] == pytest.approx(expected)

    def test_temperature_feedback_depresses_reactivity(self):
        # Pin everything except reactivity each tick; a core held at 900°C
        # must settle reactivity at -K_TEMP_REACTIVITY * 200 = -1.0.
        state = initial_state()
        state["core_temperature"] = 900.0

        for _ in range(int(5 * TAUS["reactivity"])):
            reactivity = step(state, dict(BASE_METRICS), 1.0)["reactivity"]
            state = initial_state()
            state["core_temperature"] = 900.0
            state["reactivity"] = reactivity

        assert state["reactivity"] == pytest.approx(-K_TEMP_REACTIVITY * 200.0, rel=0.01)

    def test_feedback_loop_self_stabilizes(self):
        state = initial_state()
        targets = dict(BASE_METRICS)
        targets["core_temperature"] = 1100.0

        history = []
        for _ in range(300):
            state = step(state, targets, 1.0)
            for metric in METRICS:
                low, high = PHYSICAL_RANGES[metric]
                assert low <= state[metric] <= high
            history.append(state["core_temperature"])

        settled = history[-10:]
        assert max(settled) - min(settled) < 0.01

    def test_inputs_not_mutated(self):
        state = initial_state()
        state["coolant_flow_rate"] = 60.0
        targets = dict(BASE_METRICS)
        targets["core_temperature"] = 1100.0
        state_copy = dict(state)
        targets_copy = dict(targets)

        step(state, targets, 1.0)

        assert state == state_copy
        assert targets == targets_copy
