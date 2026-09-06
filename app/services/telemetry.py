import random
from logging import getLogger

from app.models.incident_report import IncidentReportResponse, IncidentStatus

logger = getLogger(__name__)

# frozenset() accepts any iterable, including a plain parenthesised sequenc
TRACKED_INCIDENT_TYPE_CODES: frozenset[str] = frozenset(
    {
        "unrequested_fission_surplus",
        "unauthorised_power_change",
        "power_instability",
        "coolant_temperature_exceedance",
        "primary_coolant_loss",
        "heat_exchanger_failure",
        "xenon_poisoning_instability",
        "reactivity_excursion_risk",
        "control_rod_anomaly",
        "coolant_flow_reduction",
        "coolant_pump_failure",
        "steam_pressure_anomaly",
        "venting_system_malfunction",
        "radiation_release_detected",
        "radiation_level_exceedance",
        "contamination_event",
        "containment_integrity_compromised",
        "structural_integrity_concern",
    }
)

# UI: → VU meter / radial gauge (centerpiece metric)
# incident_types: unrequested_fission_surplus, unauthorised_power_change, power_instability
BASE_REACTOR_POWER_OUTPUT = 95  # 0 – 120%

# UI: → Vertical thermometer bar
# incident_types: coolant_temperature_exceedance, primary_coolant_loss, heat_exchanger_failure
BASE_CORE_TEMPERATURE = 700  # Range: 200 – 1200°C

# UI: → Oscillating line chart (real-time)
# incident_types: xenon_poisoning_instability, reactivity_excursion_risk, control_rod_anomaly
BASE_REACTIVITY = 0  # (Neutron Flux)  -5 to +5 (arbitrary units)

# UI: → Horizontal progress bar
# incident_types: coolant_flow_reduction, coolant_pump_failure, primary_coolant_loss
BASE_COOLANT_FLOW_RATE = 80  # 0 – 100%

# UI: → Dial gauge
# incident_types: steam_pressure_anomaly, venting_system_malfunction
BASE_COOLANT_PRESSURE = 130  # Range: 0 – 200 bar

# UI: → LED numeric display + blinking when high
# incident_types radiation_release_detected, radiation_level_exceedance, contamination_event
BASE_RADIATION_LEVEL = 2  # 0 – 500

# UI: → Ring progress (donut chart)
# incident_types  containment_integrity_compromised, structural_integrity_concern
BASE_CONTAINMENT_INTEGRITY = 95  # Range: 0 – 100%


STATUS_WEIGHT: dict[IncidentStatus, float] = {
    IncidentStatus.REPORTED: 0.3,
    IncidentStatus.UNDER_REVIEW: 0.6,
    IncidentStatus.CONFIRMED: 1.0,
    IncidentStatus.MITIGATION_IN_PROGRESS: 0.5,
    IncidentStatus.CONTAINED: 0.2,
    IncidentStatus.RESOLVED: 0.0,
    IncidentStatus.CLOSED: 0.0,
    IncidentStatus.FALSE_ALARM: 0.0,
}

# REPORTED → small impact
# CONFIRMED → full impact ✅
# Eg coolant_flow_reduction is effected by status REPORTED it's more effeected by CONFIRMED

# TODO look into MappingProxyType
INCIDENT_IMPACT_MAP = {
    # --- Reactor Core ---
    "unrequested_fission_surplus": {
        "reactor_power": +20,  # direct cause; pushes clearly into warning range from base 95
        "core_temperature": +50,  # more fission = more heat; secondary but real
    },
    "unauthorised_power_change": {
        "reactor_power": +15,  # worst-case upward assumption; direction is a guess
    },
    "power_instability": {
        "reactor_power": +10,  # using upward as danger direction; instability could spike either way
    },
    "coolant_temperature_exceedance": {
        "core_temperature": +200,  # this IS the temp exceeding limits; large direct impact
    },
    "primary_coolant_loss": {
        "coolant_flow_rate": -20,  # less coolant = less flow
        "core_temperature": +150,  # loss of cooling medium = heat accumulates
    },
    "heat_exchanger_failure": {
        "core_temperature": +180,  # heat not dissipated to secondary loop; major impact
    },
    # --- Reactivity ---
    "xenon_poisoning_instability": {
        "reactivity": -3.0,  # Xe-135 absorbs neutrons; classically suppresses reactivity into negative
    },
    "reactivity_excursion_risk": {
        "reactivity": +3.5,  # excursion = runaway positive reactivity; near danger threshold alone
        "reactor_power": +10,  # high reactivity drives power output up
    },
    "control_rod_anomaly": {
        "reactivity": +2.0,  # guessing rods stuck withdrawn / not inserting = uncontrolled positive reactivity
    },
    # --- Cooling System ---
    "coolant_flow_reduction": {
        "coolant_flow_rate": -25,  # this IS the flow being reduced; direct
        "core_temperature": +50,  # reduced cooling = some heat buildup
    },
    "coolant_pump_failure": {
        "coolant_flow_rate": -35,  # pump failure = near-complete flow loss; worst cooling incident
        "core_temperature": +100,  # near-complete loss of flow = significant heat rise
    },
    "steam_pressure_anomaly": {
        "coolant_pressure": +40,  # pressure problem; positive = too high. Direction is a guess — could go either way
    },
    "venting_system_malfunction": {
        "coolant_pressure": +35,  # can't vent steam = pressure builds in primary loop
    },
    # --- Radiation & Containment ---
    "radiation_release_detected": {
        "radiation_level": +30,  # detected release = immediate meaningful jump from base 2
        "containment_integrity": -3,  # implies a minor breach allowed the release; guess
    },
    "radiation_level_exceedance": {
        "radiation_level": +50,  # level already exceeding normal; large direct impact
    },
    "contamination_event": {
        "radiation_level": +20,  # spread of contamination raises ambient level
        "containment_integrity": -5,  # contamination spread often implies containment compromise; guess
    },
    "containment_integrity_compromised": {
        "containment_integrity": -15,  # direct structural damage; single event pushes into warning
        "radiation_level": +40,  # breach = unshielded radiation escape
    },
    "structural_integrity_concern": {
        "containment_integrity": -8,  # less direct than breach; concern not yet confirmed damage
    },
}


MULTIPLICATIVE_JITTER = 0.005  # ±0.5%
ADDITIVE_JITTER = 0.0025  # half of multiplicative band, applied additively at zero


def noise(
    data: dict[str, float],
    *,
    rng: random.Random | None = None,
) -> dict[str, float]:
    """Apply random noise metrics"""
    source = rng or random
    result = dict(data)
    for key, value in result.items():
        if value == 0:
            result[key] = value + source.uniform(-ADDITIVE_JITTER, ADDITIVE_JITTER)
        else:
            result[key] = value * source.uniform(1 - MULTIPLICATIVE_JITTER, 1 + MULTIPLICATIVE_JITTER)
    return result


def apply_impact(
    data: dict[str, float],
    incident_type_code: str,
    status: IncidentStatus,
) -> dict[str, float]:
    """Apply INCIDENT_IMPACT_MAP deltas to reports with status weighting"""
    result = dict(data)
    if incident_type_code not in INCIDENT_IMPACT_MAP:
        return result
    deltas = INCIDENT_IMPACT_MAP[incident_type_code]

    for key, value in deltas.items():
        # apply delta value & weight to delta key in result
        result[key] = result[key] + (value * STATUS_WEIGHT[status])
    return result


def compute_metrics(recent_reports: list[IncidentReportResponse]):
    logger.info("compute_metrics: %d recent reports", len(recent_reports))
    metrics = {
        "reactor_power": BASE_REACTOR_POWER_OUTPUT,
        "core_temperature": BASE_CORE_TEMPERATURE,
        "reactivity": BASE_REACTIVITY,
        "coolant_flow_rate": BASE_COOLANT_FLOW_RATE,
        "coolant_pressure": BASE_COOLANT_PRESSURE,
        "radiation_level": BASE_RADIATION_LEVEL,
        "containment_integrity": BASE_CONTAINMENT_INTEGRITY,
    }

    for report in recent_reports:
        logger.info("  status=%s code=%s", report.status, report.incident_type_code)
        if report.incident_type_code not in INCIDENT_IMPACT_MAP:
            continue
        metrics = apply_impact(metrics, report.incident_type_code, report.status)

    # Implement gradual drift
    metrics = noise(metrics)
    return metrics
