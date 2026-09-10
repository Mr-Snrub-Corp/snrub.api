"""Sensor layer (Phase 3, docs/roadmap.md): true state -> measured telemetry.

Each metric is read through one sensor that applies measurement error to the
plant model's true value: gaussian noise (absolute sigma in engineering
units — replaces the old whole-dict multiplicative noise() in
services/telemetry.py, whose zero-value special case existed only because
reactivity's base is 0), an optional first-order measurement lag, and a
health flag. Phase 3 ships every sensor OK; DEGRADED (noisier) and FAILED
(stuck at last reading) exist for Phase 6 fault injection.

Lag is stateful: the previous reading lives in the simulator process and is
persisted via the measured_* columns of plant_states, so filters resume
across simulator restarts.
"""

import random
from dataclasses import dataclass
from enum import StrEnum
from math import exp


class SensorHealth(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True)
class SensorSpec:
    """Error model for a single sensor. noise_sigma is absolute, in the metric's units."""

    metric: str
    noise_sigma: float
    lag_tau: float = 0.0  # seconds; 0 = no measurement lag
    health: SensorHealth = SensorHealth.OK


DEGRADED_NOISE_FACTOR = 5.0

# Sigmas ~0.5% of each metric's base value (the old jitter band), but absolute.
SENSORS: dict[str, SensorSpec] = {
    "reactor_power": SensorSpec("reactor_power", 0.5),
    "core_temperature": SensorSpec("core_temperature", 3.5, lag_tau=5.0),  # thermowell lag
    "reactivity": SensorSpec("reactivity", 0.02),
    "coolant_flow_rate": SensorSpec("coolant_flow_rate", 0.4),
    "coolant_pressure": SensorSpec("coolant_pressure", 0.65),
    "radiation_level": SensorSpec("radiation_level", 0.05, lag_tau=3.0),  # detector integration
    "containment_integrity": SensorSpec("containment_integrity", 0.2),
}


def sample(
    spec: SensorSpec,
    true_value: float,
    prev_reading: float | None,
    dt: float,
    *,
    rng: random.Random | None = None,
) -> float:
    """One sensor reading: lag toward the true value, then add gaussian noise."""
    if spec.health is SensorHealth.FAILED:
        # Stuck at the last reading; a just-booted failed sensor sticks at truth.
        return prev_reading if prev_reading is not None else true_value

    if spec.lag_tau > 0 and prev_reading is not None:
        reading = prev_reading + (true_value - prev_reading) * (1.0 - exp(-dt / spec.lag_tau))
    else:
        reading = true_value

    source = rng or random
    sigma = spec.noise_sigma * (DEGRADED_NOISE_FACTOR if spec.health is SensorHealth.DEGRADED else 1.0)
    return reading + source.gauss(0.0, sigma)


def sample_all(
    true_state: dict[str, float],
    prev_readings: dict[str, float],
    dt: float,
    *,
    rng: random.Random | None = None,
) -> dict[str, float]:
    """Sample every sensor against the true state. Inputs not mutated."""
    return {
        metric: sample(spec, true_state[metric], prev_readings.get(metric), dt, rng=rng)
        for metric, spec in SENSORS.items()
    }
