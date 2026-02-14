from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..controllers.incident_report_subject import add_subject, get_subjects, remove_subject
from ..db.database import get_session
from ..models.incident_report_subject import IncidentReportSubjectCreateRequest
from ..security.auth_bearer import JWTBearer
from ..security.authorization import verify_admin_access

router = APIRouter(prefix="/incident-reports", tags=["Incident Report Subjects"])


@router.post("/{report_id}/subjects/", dependencies=[Depends(verify_admin_access)])
async def create_one(
    report_id: UUID,
    data: IncidentReportSubjectCreateRequest,
    session: Session = Depends(get_session),
):
    return add_subject(report_id, data, session)


@router.get("/{report_id}/subjects/", dependencies=[Depends(JWTBearer())])
async def get_all(report_id: UUID, session: Session = Depends(get_session)):
    return get_subjects(report_id, session)


@router.delete("/{report_id}/subjects/{subject_uid}", dependencies=[Depends(verify_admin_access)])
async def delete_one(report_id: UUID, subject_uid: UUID, session: Session = Depends(get_session)):
    return remove_subject(report_id, subject_uid, session)
