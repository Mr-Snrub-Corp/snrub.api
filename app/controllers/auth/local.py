from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session

from app.controllers.user import pwd_context, user_crud
from app.models.auth import LoginRequest
from app.security.jwt import sign_jwt


def authenticate_user(login_data: LoginRequest, session: Session):
    """Authenticate a user with email and password"""
    # Implementation will go here
    # Query user by email using CRUD helper
    user = user_crud.get_by_email(session, login_data.email)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not pwd_context.verify(login_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Generate JWT token
    return sign_jwt(user.uid, user.to_jwt_data())


def logout_user():
    """Logout a user"""
    # For JWT-based auth, logout is primarily handled client-side
    # by removing the token from storage

    # TODO implement a token blacklist here if needed
    # to invalidate tokens before they expire
    return JSONResponse(status_code=status.HTTP_205_RESET_CONTENT, content={"message": "Successfully logged out"})
