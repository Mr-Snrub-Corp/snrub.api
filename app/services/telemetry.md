## 🔥 Reactor Core
### Reactor Power Output (%)
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


### Core Temperature (°C)
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


### Reactivity / Neutron Flux
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

______________________________

## 💧 Cooling System
### Coolant Flow Rate (%)
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


### Coolant Pressure (bar)
Range: 0 – 200 bar
Normal: 120 – 160
Warning: 100 – 120 or 160 – 180
Danger: <100 or >180

UI:
→ Dial gauge

Impacted by:

steam_pressure_anomaly
venting_system_malfunction

_________________________________________________


## ☢️ Radiation & Containment
## Radiation Level (mSv/h)
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


## Containment Integrity (%)
Range: 0 – 100%
Normal: 95 – 100%
Warning: 85 – 95%
Danger: <85%

UI:
→ Ring progress (donut chart)

Impacted by:

containment_integrity_compromised
structural_integrity_concern


## ⚡ Systems & Safety
### Backup Power Status
Values: ONLINE / DEGRADED / OFFLINE

UI:
→ Status LED (green/yellow/red)

Impacted by:

backup_power_failure
power_supply_instability


### Emergency Systems Availability (%)
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


### Alarm System Health
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