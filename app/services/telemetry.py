import random
from logging import getLogger

from app.models.incident_report import IncidentReportResponse

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


# STATUS_WEIGHT = {
#     "REPORTED": 0.3,
#     "UNDER_REVIEW": 0.6,
#     "CONFIRMED": 1.0,
#     "MITIGATION_IN_PROGRESS": 0.5,
#     "CONTAINED": 0.2,
#     "RESOLVED": 0.0,
#     "CLOSED": 0.0,
#     "FALSE_ALARM": 0.0
# }

# REPORTED → small impact
# CONFIRMED → full impact ✅
# Eg coolant_flow_reduction is effected by status REPORTED it's more effeected by CONFIRMED


def noise(data: dict[str, float]) -> dict[str, float]:
    result = dict(data)
    for x in result:
        multiplier = random.uniform(0.995, 1.005)
        if not bool(result[x]):
            result[x] += multiplier
        else:
            result[x] *= multiplier
    return result


def compute_metrics(recent_reports: list[IncidentReportResponse]):
    logger.info("compute_metrics: %d recent reports", len(recent_reports))
    for r in recent_reports:
        desc = (r.description or "")[:60]
        logger.info("  occurred_at=%s status=%s desc=%s", r.occurred_at, r.status, desc)
    base = {
        "reactor_power": BASE_REACTOR_POWER_OUTPUT,
        "core_temperature": BASE_CORE_TEMPERATURE,
        "reactivity": BASE_REACTIVITY,
        "coolant_flow_rate": BASE_COOLANT_FLOW_RATE,
        "radiation_level": BASE_RADIATION_LEVEL,
        "containment_integrity": BASE_CONTAINMENT_INTEGRITY,
    }
    # Implement gardual drift
    # Implement status weight
    base = noise(base)
    return base


"""
1. Reactor Metrics (what to simulate)

These are realistic-but-simplified and map nicely to your incident types.

🔥 Reactor Core
Reactor Power Output (%)
Range: 0 – 120%
Normal: 85 – 100%
Warning: 100 – 110%
Danger: >110%

UI:
→ VU meter / radial gauge (centerpiece metric)

Impacted by:

unrequested_fission_surplus
unauthorised_power_change
power_instability
Core Temperature (°C)
Range: 200 – 1200°C
Normal: 500 – 900°C
Warning: 900 – 1000°C
Danger: >1000°C

UI:
→ Vertical thermometer bar

Impacted by:

coolant_temperature_exceedance
primary_coolant_loss
heat_exchanger_failure
Reactivity / Neutron Flux
Range: -5 to +5 (arbitrary units)
Normal: -1 to +1
Warning: +1 to +3
Danger: >+3

UI:
→ Oscillating line chart (real-time)

Impacted by:

xenon_poisoning_instability
reactivity_excursion_risk
control_rod_anomaly
💧 Cooling System
Coolant Flow Rate (%)
Range: 0 – 100%
Normal: 70 – 100%
Warning: 50 – 70%
Danger: <50%

UI:
→ Horizontal progress bar

Impacted by:

coolant_flow_reduction
coolant_pump_failure
primary_coolant_loss
Coolant Pressure (bar)
Range: 0 – 200 bar
Normal: 120 – 160
Warning: 100 – 120 or 160 – 180
Danger: <100 or >180

UI:
→ Dial gauge

Impacted by:

steam_pressure_anomaly
venting_system_malfunction
☢️ Radiation & Containment
Radiation Level (mSv/h)
Range: 0 – 500
Normal: 0 – 5
Warning: 5 – 50
Danger: >50

UI:
→ LED numeric display + blinking when high

Impacted by:

radiation_release_detected
radiation_level_exceedance
contamination_event
Containment Integrity (%)
Range: 0 – 100%
Normal: 95 – 100%
Warning: 85 – 95%
Danger: <85%

UI:
→ Ring progress (donut chart)

Impacted by:

containment_integrity_compromised
structural_integrity_concern
⚡ Systems & Safety
Backup Power Status
Values: ONLINE / DEGRADED / OFFLINE

UI:
→ Status LED (green/yellow/red)

Impacted by:

backup_power_failure
power_supply_instability
Emergency Systems Availability (%)
Range: 0 – 100%
Normal: 100%
Warning: 70 – 99%
Danger: <70%

UI:
→ Stacked bar (ECCS, shutdown, alarms)

Impacted by:

emergency_core_cooling_unavailable
emergency_shutdown_unavailable
alarm_system_failure
Alarm System Health
Values: OK / DEGRADED / FAILED

UI:
→ Indicator with pulse animation when failed

👷 Human Factor (this is your unique twist)
Operator Alertness Index
Range: 0 – 100
Normal: 80 – 100
Warning: 50 – 80
Danger: <50

UI:
→ Bar with 👀 icon or “fatigue meter”

Impacted by:

operator_asleep_at_station
operator_intoxicated_at_station
"""
