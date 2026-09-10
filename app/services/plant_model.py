"""True-state plant integrator (Phase 3, docs/roadmap.md).

Integrates a persistent physical state toward incident-derived targets
(services/telemetry.compute_targets) with metric-to-metric coupling and one
negative temperature -> reactivity feedback term. Deterministic — measurement
noise belongs to the sensor layer (services/sensors.py).

Stability: each metric is a first-order lerp with the exact discretization
``alpha = 1 - exp(-dt / tau)``, so alpha is always in (0, 1) — unconditionally
stable and overshoot-free for any dt. The coupling graph is a DAG
(flow -> temp, power -> temp, reactivity -> power, containment -> radiation)
plus one deliberate cycle temp -> reactivity -> power -> temp whose loop gain
is ``-K_TEMP_REACTIVITY * K_REACTIVITY_POWER * K_POWER_TEMP = -0.0375``;
|gain| << 1 and negative, so the system has a unique fixed point near the
targets and converges monotonically at dt = 1s. With zero active incidents
every coupling term vanishes and the fixed point is exactly BASE_METRICS.
"""

from math import exp

from app.services.telemetry import (
    BASE_CONTAINMENT_INTEGRITY,
    BASE_COOLANT_FLOW_RATE,
    BASE_CORE_TEMPERATURE,
    BASE_METRICS,
    BASE_REACTOR_POWER_OUTPUT,
)

METRICS: tuple[str, ...] = (
    "reactor_power",
    "core_temperature",
    "reactivity",
    "coolant_flow_rate",
    "coolant_pressure",
    "radiation_level",
    "containment_integrity",
)

# Saturation limits from docs/telemetry.md. Plant-physics concern, distinct
# from the alarm/interlock bands in services/setpoints.py.
PHYSICAL_RANGES: dict[str, tuple[float, float]] = {
    "reactor_power": (0, 120),
    "core_temperature": (200, 1200),
    "reactivity": (-5, 5),
    "coolant_flow_rate": (0, 100),
    "coolant_pressure": (0, 200),
    "radiation_level": (0, 500),
    "containment_integrity": (0, 100),
}

# Time constants (seconds): how fast each metric eases toward its target.
# Gameplay-feel knobs — fast neutronics, slow thermal mass and structure.
TAUS: dict[str, float] = {
    "reactivity": 5.0,
    "reactor_power": 8.0,
    "coolant_flow_rate": 10.0,
    "coolant_pressure": 12.0,
    "radiation_level": 15.0,
    "core_temperature": 30.0,
    "containment_integrity": 45.0,
}

# Coupling gains, seeded from the cross-metric ratios in INCIDENT_IMPACT_MAP
# (mean delta ratio of the incident codes touching both metrics).
K_FLOW_TEMP = 4.0  # °C per % coolant-flow deficit
K_POWER_TEMP = 2.5  # °C per % reactor-power excess
K_REACTIVITY_POWER = 3.0  # % power per reactivity unit
K_CONTAINMENT_RADIATION = 5.0  # mSv/h per % containment deficit
K_TEMP_REACTIVITY = 0.005  # reactivity per °C above base (Doppler-style negative feedback)


def initial_state() -> dict[str, float]:
    """Quiescent plant: every metric at its base value."""
    return dict(BASE_METRICS)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _effective_targets(state: dict[str, float], targets: dict[str, float]) -> dict[str, float]:
    """Incident targets adjusted by the current state's coupling terms."""
    eff = dict(targets)
    eff["core_temperature"] += K_FLOW_TEMP * (BASE_COOLANT_FLOW_RATE - state["coolant_flow_rate"]) + K_POWER_TEMP * (
        state["reactor_power"] - BASE_REACTOR_POWER_OUTPUT
    )
    eff["reactor_power"] += K_REACTIVITY_POWER * state["reactivity"]
    eff["radiation_level"] += K_CONTAINMENT_RADIATION * (BASE_CONTAINMENT_INTEGRITY - state["containment_integrity"])
    eff["reactivity"] -= K_TEMP_REACTIVITY * (state["core_temperature"] - BASE_CORE_TEMPERATURE)
    return eff


def step(state: dict[str, float], targets: dict[str, float], dt: float) -> dict[str, float]:
    """Advance true state by dt seconds toward the targets. Inputs not mutated."""
    eff = _effective_targets(state, targets)
    result: dict[str, float] = {}
    for metric in METRICS:
        alpha = 1.0 - exp(-dt / TAUS[metric])
        value = state[metric] + (eff[metric] - state[metric]) * alpha
        result[metric] = _clamp(value, *PHYSICAL_RANGES[metric])
    return result
