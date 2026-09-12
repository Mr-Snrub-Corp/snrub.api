"""Debounced auto-incidents from plant-state excursions (Phase 4).

Each simulator tick classifies true state against SETPOINTS. DANGER is an
excursion; WARNING stays alarm-only. A metric must stay in DANGER for
DEBOUNCE_TICKS consecutive ticks before we file, and we skip if an ``[auto]``
report for that code is already open — exactly one incident per open excursion.
"""

from datetime import datetime
from logging import getLogger
from uuid import UUID

from sqlmodel import Session, select

from app.controllers.incident_report import create_report
from app.core.config import settings
from app.models.incident_report import IncidentReport, IncidentReportCreateRequest, IncidentStatus
from app.models.incident_type import IncidentType
from app.models.user import User
from app.services.alarms import AlarmLevel, classify
from app.services.setpoints import SETPOINTS, Setpoint

logger = getLogger(__name__)

DEBOUNCE_TICKS = 3
AUTO_MARKER = "[auto]"

_TERMINAL_STATUSES: frozenset[IncidentStatus] = frozenset(
    {IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.FALSE_ALARM}
)

# (metric, danger direction) → incident_type_code. Direction matches classify():
# high = value >= danger_high, low = value <= danger_low.
EXCURSION_CODE_MAP: dict[tuple[str, str], str] = {
    ("reactor_power", "high"): "unrequested_fission_surplus",
    ("core_temperature", "high"): "coolant_temperature_exceedance",
    ("reactivity", "high"): "reactivity_excursion_risk",
    ("reactivity", "low"): "xenon_poisoning_instability",
    ("coolant_flow_rate", "low"): "coolant_flow_reduction",
    ("coolant_pressure", "high"): "steam_pressure_anomaly",
    ("coolant_pressure", "low"): "steam_pressure_anomaly",
    ("radiation_level", "high"): "radiation_level_exceedance",
    ("containment_integrity", "low"): "containment_integrity_compromised",
}


def _danger_direction(value: float, setpoint: Setpoint) -> str | None:
    if setpoint.danger_high is not None and value >= setpoint.danger_high:
        return "high"
    if setpoint.danger_low is not None and value <= setpoint.danger_low:
        return "low"
    return None


def current_excursions(state: dict[str, float]) -> dict[str, str]:
    """Map metric → incident_type_code for metrics currently in the DANGER band."""
    found: dict[str, str] = {}
    for metric, value in state.items():
        setpoint = SETPOINTS.get(metric)
        if setpoint is None:
            continue
        if classify(value, setpoint) is not AlarmLevel.DANGER:
            continue
        direction = _danger_direction(value, setpoint)
        if direction is None:
            continue
        code = EXCURSION_CODE_MAP.get((metric, direction))
        if code is None:
            logger.warning("no excursion code for %s %s", metric, direction)
            continue
        found[metric] = code
    return found


def update_streaks(streaks: dict[str, int], excursions: dict[str, str]) -> tuple[dict[str, int], list[str]]:
    """Count consecutive DANGER ticks per metric.

    Recovered metrics drop out. A code is ready every tick at/after the
    debounce threshold — ``file_auto_reports`` dedups so we still file once.
    """
    next_streaks: dict[str, int] = {}
    ready: list[str] = []
    for metric, code in excursions.items():
        count = streaks.get(metric, 0) + 1
        next_streaks[metric] = count
        if count >= DEBOUNCE_TICKS:
            ready.append(code)
    return next_streaks, ready


def lookup_system_user_id(session: Session) -> UUID | None:
    user = session.exec(select(User).where(User.email == settings.SYSTEM_USER_EMAIL)).first()
    return user.uid if user else None


def _incident_type(code: str, session: Session) -> IncidentType | None:
    return session.exec(select(IncidentType).where(IncidentType.code == code)).first()


def _open_auto_report(code: str, session: Session) -> IncidentReport | None:
    """Most-recent non-terminal auto-report for this incident type."""
    incident_type = _incident_type(code, session)
    if incident_type is None:
        return None
    return session.exec(
        select(IncidentReport)
        .where(IncidentReport.incident_type_id == incident_type.uid)
        .where(IncidentReport.status.notin_(_TERMINAL_STATUSES))  # pylint: disable=no-member
        .where(IncidentReport.description.startswith(AUTO_MARKER))  # pylint: disable=no-member
        .order_by(IncidentReport.occurred_at.desc())
    ).first()


def file_auto_reports(codes: list[str], session: Session, system_user_id: UUID) -> list[str]:
    """File one [auto] report per code unless an open auto-report already exists."""
    filed: list[str] = []
    for code in dict.fromkeys(codes):
        if _open_auto_report(code, session) is not None:
            continue
        incident_type = _incident_type(code, session)
        if incident_type is None:
            logger.warning("incident type %s missing; skip auto-report", code)
            continue
        create_report(
            IncidentReportCreateRequest(
                incident_type_id=incident_type.uid,
                description=f"{AUTO_MARKER} {code}",
                severity=incident_type.default_severity,
                occurred_at=datetime.utcnow(),
            ),
            system_user_id,
            session,
        )
        filed.append(code)
    return filed


def emit(state: dict[str, float], streaks: dict[str, int], session: Session) -> None:
    """One tick: classify, debounce, dedup, file. Updates ``streaks`` in place."""
    next_streaks, ready = update_streaks(streaks, current_excursions(state))
    streaks.clear()
    streaks.update(next_streaks)
    if not ready:
        return
    user_id = lookup_system_user_id(session)
    if user_id is None:
        logger.warning("system user %s missing; skip auto-reports", settings.SYSTEM_USER_EMAIL)
        return
    file_auto_reports(ready, session, user_id)
