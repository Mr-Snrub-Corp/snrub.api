from uuid import UUID

from sqlmodel import Session

from ..db.crud_base import CRUDBase
from ..models.incident_report import (
    IncidentReport,
    IncidentReportCreateRequest,
    IncidentReportResponse,
    IncidentReportUpdateRequest,
)

report_crud = CRUDBase(IncidentReport)


def create_report(data: IncidentReportCreateRequest, reported_by_user_id: UUID, session: Session):
    report_dict = data.model_dump()
    report_dict["reported_by_user_id"] = reported_by_user_id
    report = report_crud.create(session, IncidentReport(**report_dict))
    return IncidentReportResponse.model_validate(report)


def get_report(uid: UUID, session: Session):
    report = report_crud.get(session, uid)
    return IncidentReportResponse.model_validate(report)


def get_reports(session: Session):
    reports = report_crud.get_all(session)
    return [IncidentReportResponse.model_validate(r) for r in reports]


def update_report(uid: UUID, data: IncidentReportUpdateRequest, session: Session):
    report = report_crud.update(session, uid, data)
    return IncidentReportResponse.model_validate(report)


def delete_report(uid: UUID, session: Session):
    return report_crud.delete(session, uid)
