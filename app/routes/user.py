from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.security.auth_bearer import JWTBearer
from app.security.authorization import verify_admin_access

from ..controllers.user import (
    create_user,
    delete_user,
    get_user_by_uid,
    get_users,
    update_user,
)
from ..db.database import get_session
from ..models.user import UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", dependencies=[Depends(verify_admin_access)])
async def create_one(
    user_data: UserCreateRequest, session: Session = Depends(get_session)
):
    """Create a new user in the system.

    Args:
        user_data: The user creation data

    Returns:
        User: The newly created user object
    """
    return create_user(user_data, session)


@router.get("/", dependencies=[Depends(JWTBearer())])
async def get_all(session: Session = Depends(get_session)):
    """Get all users from the system.

    Returns:
        List[User]: A list of all user objects
    """
    return get_users(session)


@router.get("/{uid}", dependencies=[Depends(JWTBearer())])
async def get_one(uid: UUID, session: Session = Depends(get_session)):
    """Get a user from the system.

    Args:
        uid: The unique identifier of the user to retrieve

    Returns:
        User: The retrieved user object
    """
    return get_user_by_uid(uid, session)


@router.put("/{uid}", dependencies=[Depends(JWTBearer())])
async def update_one(
    uid: UUID, user_data: UserUpdateRequest, session: Session = Depends(get_session)
):
    """Update an existing user in the system.

    Args:
        uid: The unique identifier of the user to update
        user_data: The user update data
    """
    return update_user(uid, user_data, session)


@router.delete("/{uid}", dependencies=[Depends(verify_admin_access)])
async def delete_one(uid: UUID, session: Session = Depends(get_session)):
    """Delete a user from the system.

    Args:
        uid: The unique identifier of the user to delete
    """
    return delete_user(uid, session)
