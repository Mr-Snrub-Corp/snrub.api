import base64
from logging import getLogger
from uuid import UUID

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlmodel import Session

from app.services.image_processing import process_photo

from ..db.crud_base import CRUDBase
from ..models.user import User, UserCreateRequest, UserResponse, UserUpdateRequest

# Set up logger
logger = getLogger(__name__)

# Instantiate CRUD handler for User model
user_crud = CRUDBase(User)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")


def create_user(user_data: UserCreateRequest, session: Session):
    """Create a new user in the database"""
    # Hash the password
    password = pwd_context.hash(user_data.password.get_secret_value())

    # Create user dict without plain password
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["password"] = password

    # Create user
    user = user_crud.create(session, User(**user_dict))
    logger.info(
        "User created successfully", extra={"user_id": str(user.uid), "email": user.email, "role": user.role.value}
    )
    return UserResponse.model_validate(user)


def get_user_by_uid(uid: UUID, session: Session):
    """Get a user from the database by UID"""
    user = user_crud.get(session, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)


def get_users(session: Session):
    """Get all users from the database"""
    users = user_crud.get_all(session)
    # Transform to response models that exclude sensitive data and convert photo bytes to base64
    return [
        UserResponse.model_validate(
            {**user.model_dump(), "photo": base64.b64encode(user.photo).decode() if user.photo else None}
        )
        for user in users
    ]


def update_user(uid: UUID, user_data: UserUpdateRequest, session: Session):
    """Update an existing user in the database"""
    # Get the existing user
    user = user_crud.get(session, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Extract data from the request, excluding unset fields
    update_data = user_data.model_dump(exclude_unset=True)

    # Handle password separately if it's being updated
    if "password" in update_data and update_data["password"] is not None:
        # Hash the new password
        password_value = update_data["password"].get_secret_value()
        hashed_password = pwd_context.hash(password_value)
        # Update the user's password directly
        user.password = hashed_password
        # Remove password from update_data to avoid SecretStr issues
        del update_data["password"]

    # Update other fields
    for key, value in update_data.items():
        setattr(user, key, value)

    # Save changes
    session.add(user)
    session.commit()
    session.refresh(user)
    return UserResponse.model_validate(user)


def delete_user(uid: UUID, session: Session):
    """Delete a user from the database"""
    return user_crud.delete(session, uid)


def upload_user_photo(uid: UUID, photo_data: bytes, session: Session):
    """Upload a photo for a user"""
    user = user_crud.get(session, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    processed_photo = process_photo(photo_data)
    user.photo = processed_photo

    session.add(user)
    session.commit()
    session.refresh(user)

    return {"message": "Photo uploaded successfully"}


def delete_user_photo(uid: UUID, session: Session):
    """Delete a user's photo"""
    user = user_crud.get(session, uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.photo = None

    session.add(user)
    session.commit()
    session.refresh(user)

    return {"message": "Photo deleted successfully"}
