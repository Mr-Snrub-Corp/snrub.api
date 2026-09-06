from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..controllers.godmode import get_levers, set_lever
from ..db.database import get_session
from ..models.godmode import GodModeLever, LeverSetRequest
from ..security.authorization import verify_super_admin_access

router = APIRouter(prefix="/godmode", tags=["God Mode"])


@router.get("/levers")
async def list_levers(
    user_data: dict = Depends(verify_super_admin_access),
    session: Session = Depends(get_session),
):
    return get_levers(session)


@router.put("/levers/{lever}")
async def set_one(
    lever: GodModeLever,
    data: LeverSetRequest,
    user_data: dict = Depends(verify_super_admin_access),
    session: Session = Depends(get_session),
):
    return set_lever(lever, data, UUID(user_data["uid"]), session)
