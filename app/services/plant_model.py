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
    BASE_COOLANT_PRESSURE,
    BASE_CORE_TEMPERATURE,
    BASE_METRICS,
    BASE_REACTIVITY,
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

# --- Actuators (Phase 4, docs/roadmap.md) -------------------------------------
# God-mode levers set these; targets_from_actuators folds them into the same
# target shape compute_targets produced, so step() integrates identically.
# Commands (rod/pump/steam) set the operating point; faults (leak/xenon) push
# away from it. Magnitudes mirror the incident deltas they replace in
# telemetry.INCIDENT_IMPACT_MAP (primary_coolant_loss, xenon_poisoning).
ACTUATOR_NOMINAL: dict[str, float] = {
    "rod_position": 50.0,  # % inserted; 50 = critical (reactivity 0)
    "pump_speed": 80.0,  # % ; drives coolant flow, nominal = base flow
    "steam_valve": 50.0,  # % open; 50 = base pressure
    "leak_rate": 0.0,  # fault; 0 = no leak
    "xenon_injection": 0.0,  # fault; 0 = no poisoning
}

ACTUATOR_RANGES: dict[str, tuple[float, float]] = dict.fromkeys(ACTUATOR_NOMINAL, (0.0, 100.0))

K_ROD_REACTIVITY = 0.1  # reactivity per % rod displaced from nominal -> ±5 at the rails
K_VALVE_PRESSURE = 1.4  # bar per % steam-valve displaced from nominal -> ±70
K_LEAK_FLOW = 0.2  # coolant-flow %-pts lost per leak unit -> -20 at leak 100
K_LEAK_TEMP = 1.5  # °C per leak unit -> +150 at leak 100
K_XENON_REACTIVITY = 0.03  # reactivity suppressed per xenon unit -> -3 at xenon 100


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


def targets_from_actuators(actuators: dict[str, float]) -> dict[str, float]:
    """Fold actuator/fault positions into plant targets (Phase 4, docs/roadmap.md).

    Replaces compute_targets(incidents) as the plant driver: commands set the
    operating point, faults push away from it. Missing actuators fall back to
    their nominal position, so an empty dict yields exactly BASE_METRICS. Only
    sets targets — coupling and clamping still happen in step().
    """

    def _value(name: str) -> float:
        return actuators.get(name, ACTUATOR_NOMINAL[name])

    rod = _value("rod_position")
    pump = _value("pump_speed")
    valve = _value("steam_valve")
    leak = _value("leak_rate")
    xenon = _value("xenon_injection")

    targets = dict(BASE_METRICS)
    # Commands — normal operating point.
    targets["reactivity"] = BASE_REACTIVITY + K_ROD_REACTIVITY * (ACTUATOR_NOMINAL["rod_position"] - rod)
    targets["coolant_flow_rate"] = pump
    targets["coolant_pressure"] = BASE_COOLANT_PRESSURE + K_VALVE_PRESSURE * (ACTUATOR_NOMINAL["steam_valve"] - valve)
    # Faults — malfunctions layered on top of the commanded point.
    targets["coolant_flow_rate"] -= K_LEAK_FLOW * leak
    targets["core_temperature"] = BASE_CORE_TEMPERATURE + K_LEAK_TEMP * leak
    targets["reactivity"] -= K_XENON_REACTIVITY * xenon
    return targets
