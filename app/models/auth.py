from uuid import UUID

from pydantic import BaseModel, EmailStr, SecretStr, field_validator

from app.models.user import validate_password_strength


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
    new_password: SecretStr

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, password: SecretStr) -> SecretStr:
        return validate_password_strength(password)
