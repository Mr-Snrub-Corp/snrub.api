from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..controllers.incident_category import get_categories, get_category
from ..db.database import get_session
from ..security.auth_bearer import JWTBearer

router = APIRouter(prefix="/incident-categories", tags=["Incident Categories"])


@router.get("/", dependencies=[Depends(JWTBearer())])
async def get_all(session: Session = Depends(get_session)):
    return get_categories(session)


@router.get("/{uid}", dependencies=[Depends(JWTBearer())])
async def get_one(uid: UUID, session: Session = Depends(get_session)):
    return get_category(uid, session)
