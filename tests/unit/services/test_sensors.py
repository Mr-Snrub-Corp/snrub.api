import random
from math import exp

import pytest

from app.services.plant_model import METRICS
from app.services.sensors import (
    DEGRADED_NOISE_FACTOR,
    SENSORS,
    SensorHealth,
    SensorSpec,
    sample,
    sample_all,
)


class RecordingRng:
    """Records gauss() calls and returns a fixed value."""

    def __init__(self, value: float = 0.0):
        self.value = value
        self.calls: list[tuple[float, float]] = []

    def gauss(self, mu: float, sigma: float) -> float:
        self.calls.append((mu, sigma))
        return self.value


class TestSample:
    def test_deterministic_with_seeded_rng(self):
        spec = SENSORS["core_temperature"]

        first = sample(spec, 700.0, 690.0, 1.0, rng=random.Random(42))
        second = sample(spec, 700.0, 690.0, 1.0, rng=random.Random(42))

        assert first == second

    def test_zero_sigma_zero_lag_returns_true_value(self):
        spec = SensorSpec("reactor_power", noise_sigma=0.0)

        assert sample(spec, 95.0, 80.0, 1.0, rng=random.Random(1)) == 95.0

    def test_absolute_noise_at_zero_true_value(self):
        # The old noise() special-cased value == 0; absolute sigma just works.
        spec = SENSORS["reactivity"]
        rng = RecordingRng(value=0.017)

        result = sample(spec, 0.0, None, 1.0, rng=rng)

        assert result == pytest.approx(0.017)
        assert rng.calls == [(0.0, spec.noise_sigma)]

    def test_lag_first_order_step_response(self):
        spec = SensorSpec("core_temperature", noise_sigma=0.0, lag_tau=5.0)

        result = sample(spec, 800.0, 700.0, 1.0, rng=random.Random(1))

        assert result == pytest.approx(700.0 + 100.0 * (1.0 - exp(-1.0 / 5.0)))

    def test_no_prev_reading_skips_lag(self):
        spec = SensorSpec("core_temperature", noise_sigma=0.0, lag_tau=5.0)

        assert sample(spec, 800.0, None, 1.0, rng=random.Random(1)) == 800.0

    def test_failed_sensor_returns_prev_reading(self):
        spec = SensorSpec("reactor_power", noise_sigma=0.5, health=SensorHealth.FAILED)
        rng = RecordingRng()

        result = sample(spec, 110.0, 96.0, 1.0, rng=rng)

        assert result == 96.0
        assert rng.calls == []  # stuck sensors draw no noise

    def test_failed_sensor_without_prev_sticks_at_truth(self):
        spec = SensorSpec("reactor_power", noise_sigma=0.5, health=SensorHealth.FAILED)

        assert sample(spec, 110.0, None, 1.0, rng=RecordingRng()) == 110.0

    def test_degraded_scales_sigma(self):
        spec = SensorSpec("reactor_power", noise_sigma=0.5, health=SensorHealth.DEGRADED)
        rng = RecordingRng()

        sample(spec, 95.0, None, 1.0, rng=rng)

        assert rng.calls == [(0.0, 0.5 * DEGRADED_NOISE_FACTOR)]


class TestSampleAll:
    def test_sensor_registry_covers_exactly_the_canonical_metrics(self):
        assert set(SENSORS) == set(METRICS)

    def test_output_keys_match_input(self):
        true_state = dict.fromkeys(SENSORS, 1.0)

        result = sample_all(true_state, {}, 1.0, rng=random.Random(7))

        assert set(result.keys()) == set(true_state.keys())

    def test_inputs_not_mutated(self):
        true_state = dict.fromkeys(SENSORS, 1.0)
        prev_readings = dict.fromkeys(SENSORS, 0.5)
        true_copy = dict(true_state)
        prev_copy = dict(prev_readings)

        sample_all(true_state, prev_readings, 1.0, rng=random.Random(7))

        assert true_state == true_copy
        assert prev_readings == prev_copy
