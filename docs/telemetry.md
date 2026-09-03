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


## ⚡ Systems & Safety - PHASE 2
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







## compute_metrics algo 

Core idea: accumulate deltas per metric, weighted by incident status

For each report in recent_reports, you want to ask: does its incident_type_code affect any of my metrics, and if so, by how much?

Step 1 — Build an impact map

A static dict mapping each incident_type_code → { metric: delta }. For example:

"primary_coolant_loss" → { "coolant_flow_rate": -25, "core_temperature": +150 }
"coolant_pump_failure" → { "coolant_flow_rate": -30 }
Deltas represent the maximum impact at full weight (i.e. CONFIRMED status).

Step 2 — Apply status weight

The commented-out STATUS_WEIGHT dict is exactly right. For each report, look up its status weight (0.0–1.0) and scale the delta:

effective_delta = base_delta * STATUS_WEIGHT[report.status]
RESOLVED / CLOSED / FALSE_ALARM → weight 0.0 means zero contribution. CONFIRMED → full delta.

Step 3 — Accumulate across all reports

Sum the effective deltas for each metric across all reports. Multiple reports of the same type stack — which is realistic (two simultaneous coolant losses compound).

You may want to clamp accumulation so you don't go below 0 or exceed physical limits.

Step 4 — Gradual drift

Drift is the key subtlety. Rather than snapping to base + total_delta, you want the value to move toward the target over time. The pattern is a lerp (linear interpolation):

current = current + (target - current) * drift_rate
Where drift_rate is a small factor (e.g. 0.05 per poll cycle). This means the metric eases toward danger when incidents appear, and eases back toward base when they resolve — without abrupt jumps.

To implement this, compute_metrics needs to know the previous metric values, not just recalculate from base each call. You'll need some form of state persistence between calls (module-level dict, a cache, or passed in as a parameter).

Step 5 — Apply noise last

Your existing noise() goes on top at the very end, after drift and delta are resolved — small jitter on an already-adjusted value.

The order of operations:

target = base + sum(delta * status_weight for each matching report)
target = clamp(target, min, max)
current = lerp(current → target, drift_rate)
output = noise(current)
The key decision to make: where does current state live between poll cycles? That's what unlocks drift working correctly.


### The natural phases:

Now — impact map + status-weighted deltas + clamping
Later — introduce _current_state persistence and lerp toward target
When you move to phase 2, the only structural change is that compute_metrics stops recalculating from BASE_* every call and instead mutates a persistent state dict toward the weighted target. The impact map and status weights you build now carry over unchanged.