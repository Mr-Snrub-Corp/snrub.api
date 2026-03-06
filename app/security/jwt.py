import time
from uuid import UUID

import jwt

from app.core.config import settings
from app.models.user import LoginResponse, UserRole


def create_token_response(token: str, user_data: dict) -> dict:
    """Create a response containing both token and user data"""
    return {"access_token": token, "user": user_data}


def sign_jwt(user_uid: UUID, user_data: dict[str, str | UUID | UserRole]) -> LoginResponse:
    """
    Generate and sign a JWT token
    Args:
        user_uid: User's UUID
        user_data: Dictionary containing user information
    Returns:
        LoginResponse: Object containing access token and user data
    """
    payload = {
        "user_uid": str(user_uid),
        "user_data": user_data,
        "exp": int(time.time()) + (settings.JWT_EXPIRES_MINUTES * 60),
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return LoginResponse(access_token=token, user=user_data)


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError:
        return {}
