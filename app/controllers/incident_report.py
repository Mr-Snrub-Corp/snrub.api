from datetime import datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from ..db.crud_base import CRUDBase
from ..models.incident_report import (
    IncidentReport,
    IncidentReportCreateRequest,
    IncidentReportResponse,
    IncidentReportTelemetry,
    IncidentReportUpdateRequest,
)
from ..models.incident_report_subject import (
    IncidentReportSubject,
    IncidentReportSubjectResponse,
)
from ..models.incident_type import IncidentType
from ..models.user import User

report_crud = CRUDBase(IncidentReport)


def _get_subjects(report_uid: UUID, session: Session) -> list[IncidentReportSubjectResponse]:
    subjects = session.exec(
        select(IncidentReportSubject).where(IncidentReportSubject.incident_report_id == report_uid)
    ).all()
    return [IncidentReportSubjectResponse.model_validate(s) for s in subjects]


def _replace_subjects(report_uid: UUID, subjects_data: list, session: Session):
    existing = session.exec(
        select(IncidentReportSubject).where(IncidentReportSubject.incident_report_id == report_uid)
    ).all()
    for s in existing:
        session.delete(s)
    for s_data in subjects_data:
        subject = IncidentReportSubject(incident_report_id=report_uid, **s_data.model_dump())
        session.add(subject)


def _to_response(report: IncidentReport, session: Session) -> IncidentReportResponse:
    subjects = _get_subjects(report.uid, session)
    return IncidentReportResponse(**report.model_dump(), subjects=subjects)


def create_report(data: IncidentReportCreateRequest, reported_by_user_id: UUID, session: Session):
    if not session.get(User, reported_by_user_id):
        raise HTTPException(status_code=401, detail="User not found")

    report_dict = data.model_dump(exclude={"subjects"})
    report_dict["reported_by_user_id"] = reported_by_user_id
    report = IncidentReport(**report_dict)
    session.add(report)
    session.flush()

    for s_data in data.subjects:
        subject = IncidentReportSubject(incident_report_id=report.uid, **s_data.model_dump())
        session.add(subject)

    session.commit()
    session.refresh(report)
    return _to_response(report, session)


def get_report(uid: UUID, session: Session):
    report = report_crud.get(session, uid)
    return _to_response(report, session)


def get_reports(
    session: Session,
    offset: int,
    limit: int | None,
    status: list[str] | None,
    incident_type_codes: list[str] | None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    query = select(IncidentReport)
    if status:
        query = query.where(IncidentReport.status.in_(status))  # pylint: disable=no-member
    if incident_type_codes:
        # builds an inner SELECT uid FROM incident_types
        subquery = select(IncidentType.uid).where(
            # narrows it to just your tracked codes
            IncidentType.code.in_(incident_type_codes)  # pylint: disable=no-member
        )
        query = query.where(IncidentReport.incident_type_id.in_(subquery))  # pylint: disable=no-member
    if date_from:
        query = query.where(IncidentReport.occurred_at >= date_from)
    if date_to:
        query = query.where(IncidentReport.occurred_at <= date_to)
    query = query.order_by(IncidentReport.occurred_at.desc()).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    reports = session.exec(query).all()
    return [_to_response(r, session) for r in reports]


def get_reports_for_telemetry(
    session: Session,
    status: list[str] | None,
    incident_type_codes: list[str] | None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
):
    now = datetime.utcnow()
    if date_to is None:
        date_to = now
    if date_from is None:
        date_from = now - timedelta(weeks=1)
    rows = session.exec(
        select(IncidentType.code, IncidentReport.status)
        .join(IncidentType)
        .where(IncidentReport.status.in_(status))  # pylint: disable=no-member
        .where(
            IncidentType.code.in_(incident_type_codes)  # pylint: disable=no-member
        )
        .where(IncidentReport.occurred_at >= date_from)
        .where(IncidentReport.occurred_at <= date_to)
    )
    return [IncidentReportTelemetry(incident_type_code=code, status=status) for code, status in rows]


def update_report(uid: UUID, data: IncidentReportUpdateRequest, session: Session):
    report = session.exec(select(IncidentReport).where(IncidentReport.uid == uid)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")

    obj_data = data.model_dump(exclude_unset=True, exclude={"subjects"})
    for key, value in obj_data.items():
        setattr(report, key, value)

    if data.subjects is not None:
        _replace_subjects(report.uid, data.subjects, session)

    session.add(report)
    session.commit()
    session.refresh(report)
    return _to_response(report, session)


def delete_report(uid: UUID, session: Session):
    report_crud.delete(session, uid)
