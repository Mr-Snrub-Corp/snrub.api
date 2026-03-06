import logging
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, SQLModel

from app.controllers.user import pwd_context, user_crud
from app.db.crud_base import CRUDBase
from app.models.auth import PerformPasswordResetRequest, RequestPasswordResetRequest
from app.models.password_reset import PasswordReset
from app.services.email import send_password_reset_email

# Set up logger
logger = logging.getLogger(__name__)

# Create CRUD handler for PasswordReset model - uses 'token' as primary key
password_reset_crud = CRUDBase(PasswordReset, primary_key_field="token")


# Update models for CRUD operations
class TokenUpdate(SQLModel):
    """Model for token updates"""

    used: bool = True


class UserPasswordUpdate(SQLModel):
    """Model for user password updates"""

    password: str


def create_reset_token(user_id: UUID, session: Session) -> PasswordReset:
    """Create a new password reset token and invalidate previous ones"""

    # Get active tokens for this user using the CRUD helper
    active_tokens = password_reset_crud.get_multi_by_field(session, "user_id", user_id)

    # Filter for only unexpired, unused tokens
    current_time = datetime.utcnow()
    active_tokens = [token for token in active_tokens if not token.used and token.expires_at > current_time]

    # Invalidate previous tokens using CRUD helper
    for token in active_tokens:
        password_reset_crud.update(session, token.token, TokenUpdate(used=True))

    # Create new token
    new_token = PasswordReset.create_token(user_id)

    # Use CRUD helper to save
    return password_reset_crud.create(session, new_token)


async def reset_password(reset_data: RequestPasswordResetRequest, session: Session):
    """Request a password reset token"""
    # Find user by email
    user = user_crud.get_by_email(session, reset_data.email)

    # If user doesn't exist, still return success to prevent email enumeration
    if not user:
        return {"message": "If your email is registered, you will receive a password reset link"}

    # Create new token and invalidate existing ones
    token = create_reset_token(user.uid, session)

    # Send email with reset link - make sure to await this
    await send_password_reset_email(user.email, token.token)

    return {"message": "If your email is registered, you will receive a password reset link"}


def perform_password_reset(reset_data: PerformPasswordResetRequest, session: Session):
    """Reset password using a token"""
    logger.debug(f"Reset attempt with token: {reset_data.token} (type: {type(reset_data.token)})")

    # Get the token
    try:
        logger.debug("About to query token from database")
        token = password_reset_crud.get_by_field(session, "token", reset_data.token)
        if not token:
            raise HTTPException(status_code=404, detail="Token not found")
        logger.debug(f"Token found: {token.token} (used: {token.used}, expires: {token.expires_at})")

    except HTTPException as he:
        logger.error(f"HTTP exception retrieving token: {str(he)}")
        raise HTTPException(status_code=400, detail="Invalid token") from None

    except Exception as e:
        logger.exception(f"Error retrieving token: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid token") from None

    # Validate token
    current_time = datetime.utcnow()
    if token.used or token.expires_at <= current_time:
        logger.warning(
            f"Token validation failed: used={token.used}, expires_at={token.expires_at}, current_time={current_time}"
        )
        raise HTTPException(status_code=400, detail="Token is expired or has been used")

    # Get the user
    user = user_crud.get(session, token.user_id)

    # Update the password using the CRUD helper
    update_data = UserPasswordUpdate(password=pwd_context.hash(reset_data.new_password.get_secret_value()))
    user_crud.update(session, user.uid, update_data)

    # Mark token as used - use direct attribute update instead of CRUD update (designed to work with models that have a
    # uid field as their primary key:)
    token.used = True
    session.add(token)
    session.commit()

    logger.info(f"Password reset successful for user: {user.email}")
    return {"message": "Password reset successfully"}
