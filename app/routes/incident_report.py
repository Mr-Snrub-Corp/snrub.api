from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from ..controllers.incident_report import create_report, delete_report, get_report, get_reports, update_report
from ..db.database import get_session
from ..models.incident_report import IncidentReportCreateRequest, IncidentReportUpdateRequest
from ..security.auth_bearer import JWTBearer
from ..security.authorization import verify_admin_access, verify_creator_access

router = APIRouter(prefix="/incident-reports", tags=["Incident Reports"])


@router.post("/")
async def create_one(
    data: IncidentReportCreateRequest,
    user_data: dict = Depends(verify_creator_access),
    session: Session = Depends(get_session),
):
    return create_report(data, UUID(user_data["uid"]), session)


@router.get("/", dependencies=[Depends(JWTBearer())])
async def get_all(
    session: Session = Depends(get_session), offset: int = 0, limit: int | None = None, status: list[str] = Query(None)
):
    return get_reports(session, offset, limit, status)


@router.get("/{uid}", dependencies=[Depends(JWTBearer())])
async def get_one(uid: UUID, session: Session = Depends(get_session)):
    return get_report(uid, session)


@router.put("/{uid}", dependencies=[Depends(verify_admin_access)])
async def update_one(uid: UUID, data: IncidentReportUpdateRequest, session: Session = Depends(get_session)):
    return update_report(uid, data, session)


@router.delete("/{uid}", dependencies=[Depends(verify_admin_access)])
async def delete_one(uid: UUID, session: Session = Depends(get_session)):
    return delete_report(uid, session)
