from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..controllers.incident_type import create_type, get_type, get_types, get_types_by_category, update_type
from ..db.database import get_session
from ..models.incident_type import IncidentTypeCreateRequest, IncidentTypeUpdateRequest
from ..security.auth_bearer import JWTBearer
from ..security.authorization import verify_admin_access

router = APIRouter(prefix="/incident-types", tags=["Incident Types"])


@router.post("/", dependencies=[Depends(verify_admin_access)])
async def create_one(data: IncidentTypeCreateRequest, session: Session = Depends(get_session)):
    return create_type(data, session)


@router.get("/", dependencies=[Depends(JWTBearer())])
async def get_all(category_id: UUID | None = None, session: Session = Depends(get_session)):
    if category_id:
        return get_types_by_category(category_id, session)
    return get_types(session)


@router.get("/{uid}", dependencies=[Depends(JWTBearer())])
async def get_one(uid: UUID, session: Session = Depends(get_session)):
    return get_type(uid, session)


@router.put("/{uid}", dependencies=[Depends(verify_admin_access)])
async def update_one(uid: UUID, data: IncidentTypeUpdateRequest, session: Session = Depends(get_session)):
    return update_type(uid, data, session)
