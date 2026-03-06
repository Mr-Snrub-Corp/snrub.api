from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session

from app.security.auth_bearer import JWTBearer
from app.security.authorization import verify_admin_access, verify_self_or_admin

from ..controllers.user import (
    create_user,
    delete_user,
    delete_user_photo,
    get_user_by_uid,
    get_users,
    update_user,
    upload_user_photo,
)
from ..db.database import get_session
from ..models.user import UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", dependencies=[Depends(verify_admin_access)])
async def create_one(user_data: UserCreateRequest, session: Session = Depends(get_session)):
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


@router.put("/{uid}")
async def update_one(
    uid: UUID,
    user_data: UserUpdateRequest,
    caller: dict = Depends(verify_self_or_admin),
    session: Session = Depends(get_session),
):
    """Update an existing user in the system."""
    return update_user(uid, user_data, session, caller)


@router.delete("/{uid}", dependencies=[Depends(verify_admin_access)])
async def delete_one(uid: UUID, session: Session = Depends(get_session)):
    """Delete a user from the system.

    Args:
        uid: The unique identifier of the user to delete
    """
    return delete_user(uid, session)


@router.put("/{uid}/photo", dependencies=[Depends(verify_admin_access)])
async def upload_photo(uid: UUID, file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Upload a photo for a user.

    Args:
        uid: The unique identifier of the user
        file: The PNG image file to upload
    """
    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Only PNG images are allowed")

    photo_data = await file.read()

    return upload_user_photo(uid, photo_data, session)


@router.delete("/{uid}/photo", dependencies=[Depends(verify_admin_access)])
async def delete_photo(uid: UUID, session: Session = Depends(get_session)):
    """Delete a user's photo.

    Args:
        uid: The unique identifier of the user
    """
    return delete_user_photo(uid, session)
