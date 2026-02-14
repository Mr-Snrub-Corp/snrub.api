from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models.incident_report import IncidentReport
from ..models.incident_report_subject import (
    IncidentReportSubject,
    IncidentReportSubjectCreateRequest,
    IncidentReportSubjectResponse,
)


def _get_report_or_404(report_id: UUID, session: Session) -> IncidentReport:
    report = session.exec(select(IncidentReport).where(IncidentReport.uid == report_id)).first()
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")
    return report


def add_subject(report_id: UUID, data: IncidentReportSubjectCreateRequest, session: Session):
    _get_report_or_404(report_id, session)
    subject = IncidentReportSubject(incident_report_id=report_id, **data.model_dump())
    session.add(subject)
    session.commit()
    session.refresh(subject)
    return IncidentReportSubjectResponse.model_validate(subject)


def get_subjects(report_id: UUID, session: Session):
    subjects = session.exec(
        select(IncidentReportSubject).where(IncidentReportSubject.incident_report_id == report_id)
    ).all()
    return [IncidentReportSubjectResponse.model_validate(s) for s in subjects]


def remove_subject(report_id: UUID, subject_uid: UUID, session: Session):
    subject = session.exec(
        select(IncidentReportSubject).where(
            IncidentReportSubject.uid == subject_uid,
            IncidentReportSubject.incident_report_id == report_id,
        )
    ).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    session.delete(subject)
    session.commit()
