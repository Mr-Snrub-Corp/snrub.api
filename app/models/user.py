import base64
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, SecretStr, field_validator
from sqlalchemy import Column, LargeBinary
from sqlmodel import Field, Relationship, SQLModel

# If you're using TYPE_CHECKING for better type hints without circular imports:
if TYPE_CHECKING:
    from .password_reset import PasswordReset


class UserRole(StrEnum):
    VIEWER = "viewer"
    CREATOR = "creator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DECEASED = "deceased"
    SUSPENDED = "suspended"


def validate_password_strength(password: SecretStr | None) -> SecretStr | None:
    """Validate password meets security requirements"""

    if password is None:
        return None

    value = password.get_secret_value()
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must contain at least one digit")
    if not any(char.isupper() for char in value):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in value):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(char in "!@#$%^&*()-_=+[]{}|;:,.<>?/`~" for char in value):
        raise ValueError("Password must contain at least one special character")
    return password


class UserBase(SQLModel, table=False):
    """Base User model with common fields"""

    email: EmailStr
    name: str
    role: UserRole = Field(default=UserRole.VIEWER)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    photo: str | None = None  # base64 encoded


class User(UserBase, table=True):
    """Database User model"""

    __tablename__ = "users"

    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    password: str
    photo: bytes | None = Field(default=None, sa_column=Column(LargeBinary))
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)

    def to_jwt_data(self) -> dict:
        """Build user_data dict for JWT payloads."""
        return {"uid": str(self.uid), "email": self.email, "name": self.name, "role": self.role}

    # Relationship to PasswordReset model
    password_resets: list["PasswordReset"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class UserCreateRequest(UserBase):
    """API model for user creation requests"""

    password: SecretStr

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: SecretStr) -> SecretStr:
        return validate_password_strength(password)


class UserUpdateRequest(SQLModel):
    """API model for user update requests"""

    email: EmailStr | None = None
    name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
    password: SecretStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, password: SecretStr | None) -> SecretStr | None:
        return validate_password_strength(password)


class UserResponse(UserBase):
    """API model for user responses"""

    uid: UUID
    created: datetime
    updated: datetime
    photo: str | None = None  # base64 encoded

    @field_validator("photo", mode="before")
    @classmethod
    def convert_photo_bytes(cls, v: bytes | str | None) -> str | None:
        if isinstance(v, bytes):
            return base64.b64encode(v).decode()
        return v


class LoginResponse(BaseModel):
    """Pydantic model for login response including token and user data."""

    access_token: str
    user: dict[str, str | UUID | UserRole]  # Basic user info
