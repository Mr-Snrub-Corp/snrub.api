from logging import getLogger

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session
from starlette.requests import Request

from app.core.config import settings
from app.db.crud_base import CRUDBase
from app.db.database import get_session
from app.models.user import LoginResponse, User, UserRole
from app.security.jwt import sign_jwt
from app.security.oauth_client import oauth

logger = getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Authentication"])
user_crud = CRUDBase(User)


@router.get("/login")
async def login(request: Request):
    """Login route"""
    redirect_uri = settings.GOOGLE_AUTH_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request, session: Session = Depends(get_session)):
    """Callback route"""

    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        logger.error("OAuth error during callback: %s", error.error)
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/auth/callback?provider=google&success=false&error=auth_failed"
        )
    user_info = token.get("userinfo")

    # Find or create user based on email
    email = user_info.get("email")
    existing_user = user_crud.get_by_email(session, email)

    if existing_user:
        user = existing_user
    else:
        new_user = User(
            email=email,
            name=user_info.get("name", email),
            role=UserRole.VIEWER,
            password="",  # OAuth users don't need password
        )
        user = user_crud.create(session, new_user)

    # Generate JWT token and store in session for secure retrieval
    user_data = user.to_jwt_data()
    token_response = sign_jwt(user.uid, user_data)

    request.session["auth_token"] = token_response.access_token
    request.session["auth_user"] = user_data

    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?provider=google&success=true"
    )


@router.get("/token", response_model=LoginResponse)
async def get_token(request: Request):
    """Exchange server session for JWT token after OAuth redirect"""
    token = request.session.pop("auth_token", None)
    user = request.session.pop("auth_user", None)
    if not token:
        raise HTTPException(status_code=401, detail="No pending authentication")
    return LoginResponse(access_token=token, user=user)
