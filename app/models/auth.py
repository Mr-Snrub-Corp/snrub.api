from uuid import UUID

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Pydantic model for handling login request data with email and password."""

    email: EmailStr
    password: str


class RequestPasswordResetRequest(BaseModel):
    """Request model for requesting a password reset"""

    email: EmailStr


class PerformPasswordResetRequest(BaseModel):
    """Request model for performing a password reset"""

    token: UUID
    new_password: str
