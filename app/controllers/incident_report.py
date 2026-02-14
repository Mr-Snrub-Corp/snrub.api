from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models.incident_report import (
    IncidentReport,
    IncidentReportCreateRequest,
    IncidentReportResponse,
    IncidentReportUpdateRequest,
)
from ..models.incident_report_subject import (
    IncidentReportSubject,
    IncidentReportSubjectResponse,
)


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
    report = session.exec(select(IncidentReport).where(IncidentReport.uid == uid)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")
    return _to_response(report, session)


def get_reports(session: Session):
    reports = session.exec(select(IncidentReport)).all()
    return [_to_response(r, session) for r in reports]


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
    report = session.exec(select(IncidentReport).where(IncidentReport.uid == uid)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")
    session.delete(report)
    session.commit()
