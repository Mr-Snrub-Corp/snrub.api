from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.controllers.auth.local import authenticate_user, logout_user
from app.controllers.auth.password_reset import perform_password_reset, reset_password
from app.db.database import get_session
from app.models.auth import LoginRequest, PerformPasswordResetRequest, RequestPasswordResetRequest
from app.security.auth_bearer import JWTBearer

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Routes will be added here
@router.post("/login")
async def login(login_data: LoginRequest, session: Session = Depends(get_session)):
    """Login route"""

    return authenticate_user(login_data, session)

@router.post("/logout", dependencies=[Depends(JWTBearer())])
async def logout():
    """Logout route"""
    return logout_user()

@router.post("/request-password-reset")
async def request_password_reset(
    reset_data: RequestPasswordResetRequest,
    session: Session = Depends(get_session)
):
    # Make sure to await the async function
    return await reset_password(reset_data, session)

@router.post("/reset-password")
def reset_password_with_token(
    reset_data: PerformPasswordResetRequest,
    session: Session = Depends(get_session)
):
    # This function is not async, so no await needed
    return perform_password_reset(reset_data, session)


# https://stackoverflow.com/questions/32060478/is-a-refresh-token-really-necessary-when-using-jwt-token-authentication

# The most important decision is how to handle token invalidation.
# Your current architecture uses JWTs without refresh tokens, so implementing a token
# blacklist would be the most straightforward approach for truly invalidating tokens before they expire.
