from logging import getLogger

from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends

# from sqlmodel import Session
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlmodel import Session
from starlette.requests import Request

from app.core.config import settings

# from app.db.database import get_session
from app.db.crud_base import CRUDBase
from app.db.database import get_session
from app.models.user import User, UserRole
from app.security.jwt import sign_jwt
from app.security.oauth_client import oauth

logger = getLogger(__name__)

router = APIRouter(prefix="/auth/google", tags=["Authentication"])
user_crud = CRUDBase(User)


# Routes will be added here
@router.get("/login")
async def login(request: Request):
    """Login route"""

    # Log OAuth client configuration
    logger.info(
        f"Google OAuth client configuration: client_id={settings.GOOGLE_CLIENT_ID}, "
        f"client_secret_set={bool(settings.GOOGLE_CLIENT_SECRET)}, "
        f"redirect_uri={settings.GOOGLE_AUTH_REDIRECT_URI}, "
        f"oauth_client_initialized={oauth is not None}"
    )
    redirect_uri = settings.GOOGLE_AUTH_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def callback(request: Request, session: Session = Depends(get_session)):
    """Callback route"""

    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        return HTMLResponse(f"<h1>{error.error}</h1>")
    user_info = token.get("userinfo")
    # if user:
    #     request.session['user'] = dict(user)

    # Find or create user based on email
    email = user_info.get("email")
    existing_user = user_crud.get_by_email(session, email)

    if existing_user:
        # User exists, update if needed
        user = existing_user
    else:
        # Create new user
        new_user = User(
            email=email,
            name=user_info.get("name", email),
            role=UserRole.VIEWER,
            password="",  # OAuth users don't need password
        )
        user = user_crud.create(session, new_user)

    # Generate JWT token
    user_data = {"uid": str(user.uid), "email": user.email, "name": user.name, "role": user.role}

    token_response = sign_jwt(user.uid, user_data)

    # Redirect with token in fragment
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/callback?provider=google&success=true#token={token_response.access_token}"
    )
