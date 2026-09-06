from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models.godmode import GodModeLever, LeverSetRequest, LeverState
from ..models.incident_report import (
    IncidentReport,
    IncidentReportCreateRequest,
    IncidentReportUpdateRequest,
    IncidentStatus,
)
from ..models.incident_type import IncidentType
from ..services.telemetry import STATUS_WEIGHT
from .incident_report import create_report, update_report

# Levers map onto existing incident_type_codes so compute_metrics already responds.
LEVER_CODE_MAP: dict[GodModeLever, str] = {
    GodModeLever.COOLANT_FLOW: "coolant_flow_reduction",
    GodModeLever.CONTROL_ROD: "control_rod_anomaly",
    GodModeLever.PRIMARY_COOLANT_LOSS: "primary_coolant_loss",
    GodModeLever.STEAM_PRESSURE: "steam_pressure_anomaly",
    GodModeLever.XENON: "xenon_poisoning_instability",
}

# Statuses that mean the malfunction is no longer steering telemetry ("off").
_OFF_STATUSES: frozenset[IncidentStatus] = frozenset(
    {IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.FALSE_ALARM}
)

# Marks reports authored by God mode so the lever only ever touches its own reports
# (never a genuine operator-filed incident of the same type) and they stay filterable.
GOD_MODE_MARKER = "[god-mode]"


def _god_mode_description(lever: GodModeLever) -> str:
    return f"{GOD_MODE_MARKER} simulated malfunction lever: {lever.value}"


def _get_incident_type(code: str, session: Session) -> IncidentType:
    incident_type = session.exec(select(IncidentType).where(IncidentType.code == code)).first()
    if not incident_type:
        raise HTTPException(status_code=404, detail=f"Incident type '{code}' not found")
    return incident_type


def _current_report(incident_type_id: UUID, session: Session) -> IncidentReport | None:
    """Most-recent non-terminal God-mode report for this incident type (the lever's backing report)."""
    return session.exec(
        select(IncidentReport)
        .where(IncidentReport.incident_type_id == incident_type_id)
        .where(IncidentReport.status.notin_(_OFF_STATUSES))  # pylint: disable=no-member
        .where(IncidentReport.description.startswith(GOD_MODE_MARKER))  # pylint: disable=no-member
        .order_by(IncidentReport.occurred_at.desc())
    ).first()


def _lever_state(lever: GodModeLever, code: str, report: IncidentReport | None) -> LeverState:
    if report is None:
        return LeverState(
            lever=lever,
            incident_type_code=code,
            active=False,
            status=None,
            intensity=0.0,
            report_uid=None,
        )
    intensity = STATUS_WEIGHT.get(report.status, 0.0)
    return LeverState(
        lever=lever,
        incident_type_code=code,
        active=intensity > 0.0,
        status=report.status,
        intensity=intensity,
        report_uid=report.uid,
    )


def set_lever(lever: GodModeLever, data: LeverSetRequest, user_id: UUID, session: Session) -> LeverState:
    """Create or adjust the lever's malfunction report and set its status (drives STATUS_WEIGHT)."""
    code = LEVER_CODE_MAP[lever]
    incident_type = _get_incident_type(code, session)
    existing = _current_report(incident_type.uid, session)

    if existing is not None:
        update_report(existing.uid, IncidentReportUpdateRequest(status=data.status), session)
    elif data.status not in _OFF_STATUSES:
        # create_report has no status field (defaults to REPORTED); set the requested status after.
        created = create_report(
            IncidentReportCreateRequest(
                incident_type_id=incident_type.uid,
                description=_god_mode_description(lever),
                severity=data.severity or incident_type.default_severity,
                occurred_at=datetime.utcnow(),
            ),
            user_id,
            session,
        )
        if data.status != IncidentStatus.REPORTED:
            update_report(created.uid, IncidentReportUpdateRequest(status=data.status), session)
    # else: no backing report and lever set to off -> nothing to do.

    return _lever_state(lever, code, _current_report(incident_type.uid, session))


def get_levers(session: Session) -> list[LeverState]:
    """Current state of all levers, derived from their backing incident reports."""
    states: list[LeverState] = []
    for lever, code in LEVER_CODE_MAP.items():
        incident_type = session.exec(select(IncidentType).where(IncidentType.code == code)).first()
        report = _current_report(incident_type.uid, session) if incident_type else None
        states.append(_lever_state(lever, code, report))
    return states
