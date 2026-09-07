"""Per-metric warning/danger bands, extracted from docs/telemetry.md prose.

Single shared source of truth consumed by alarm evaluation now
(services/alarms.py) and the SCRAM interlock later (Phase 5) - DRY.

Thresholds are directional and inclusive of the band edge:

- ``warning_high`` / ``danger_high``: value at or above the threshold is
  WARNING / DANGER (metrics that fail high, e.g. core temperature).
- ``warning_low`` / ``danger_low``: value at or below the threshold is
  WARNING / DANGER (metrics that fail low, e.g. coolant flow).

Unused sides are ``None``. ``coolant_pressure`` uses all four (fails both ways).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Setpoint:
    """Warning/danger thresholds for a single metric. Unused sides are None."""

    metric: str
    warning_low: float | None = None
    warning_high: float | None = None
    danger_low: float | None = None
    danger_high: float | None = None


# Bands transcribed from docs/telemetry.md. Keyed by the metric names emitted by
# services/telemetry.compute_metrics.
SETPOINTS: dict[str, Setpoint] = {
    # Normal 85-100, Warning 100-110, Danger >110 (fails high)
    "reactor_power": Setpoint("reactor_power", warning_high=100, danger_high=110),
    # Normal 500-900, Warning 900-1000, Danger >1000 (fails high)
    "core_temperature": Setpoint("core_temperature", warning_high=900, danger_high=1000),
    # Normal -1..+1, Warning +1..+3, Danger >+3 (fails high)
    "reactivity": Setpoint("reactivity", warning_high=1, danger_high=3),
    # Normal 70-100, Warning 50-70, Danger <50 (fails low)
    "coolant_flow_rate": Setpoint("coolant_flow_rate", warning_low=70, danger_low=50),
    # Normal 120-160, Warning 100-120 or 160-180, Danger <100 or >180 (fails both ways)
    "coolant_pressure": Setpoint(
        "coolant_pressure",
        warning_low=120,
        warning_high=160,
        danger_low=100,
        danger_high=180,
    ),
    # Normal 0-5, Warning 5-50, Danger >50 (fails high)
    "radiation_level": Setpoint("radiation_level", warning_high=5, danger_high=50),
    # Normal 95-100, Warning 85-95, Danger <85 (fails low)
    "containment_integrity": Setpoint("containment_integrity", warning_low=95, danger_low=85),
}
