"""Publisher-side alarm evaluation.

Maps current metric values to an alarm level using the shared bands in
``services/setpoints.py``. Pure and DB/MQTT-free so it is trivially unit
testable; the simulator loop (app/simulator.py) turns the
levels into retained ``snrub/alarms/{metric}`` messages.
"""

from datetime import UTC, datetime
from enum import StrEnum

from app.services.setpoints import SETPOINTS, Setpoint


class AlarmLevel(StrEnum):
    NORMAL = "normal"
    WARNING = "warning"
    DANGER = "danger"


def classify(value: float, setpoint: Setpoint) -> AlarmLevel:
    """Classify a single value against its setpoint. Danger takes precedence."""
    if setpoint.danger_high is not None and value >= setpoint.danger_high:
        return AlarmLevel.DANGER
    if setpoint.danger_low is not None and value <= setpoint.danger_low:
        return AlarmLevel.DANGER
    if setpoint.warning_high is not None and value >= setpoint.warning_high:
        return AlarmLevel.WARNING
    if setpoint.warning_low is not None and value <= setpoint.warning_low:
        return AlarmLevel.WARNING
    return AlarmLevel.NORMAL


def evaluate(metrics: dict[str, float]) -> dict[str, AlarmLevel]:
    """Map metric values to alarm levels. Metrics without a setpoint are skipped."""
    return {metric: classify(value, SETPOINTS[metric]) for metric, value in metrics.items() if metric in SETPOINTS}


def alarm_payload(metric: str, level: AlarmLevel, value: float) -> dict[str, object]:
    """Retained-message payload for snrub/alarms/{metric}."""
    return {
        "metric": metric,
        "level": level.value,
        "value": value,
        "ts": datetime.now(UTC).isoformat(),
    }
