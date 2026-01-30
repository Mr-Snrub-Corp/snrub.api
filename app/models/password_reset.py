from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from .user import User


class PasswordReset(SQLModel, table=True):
    """Model for password reset tokens"""
    __tablename__ = "password_resets"

    token: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.uid")
    expires_at: datetime = Field(...)
    used: bool = Field(default=False)

    # Relationship to User model
    user: User | None = Relationship(back_populates="password_resets")

    @classmethod
    def create_token(cls, user_id: UUID, expires_in_hours: int = 24) -> "PasswordReset":
        """Create a new password reset token"""
        return cls(
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours)
        )
