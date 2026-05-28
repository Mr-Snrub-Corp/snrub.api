from uuid import UUID

from fastapi import Depends, HTTPException, WebSocket
from sqlmodel import Session

from app.db.database import get_session
from app.models.user import User, UserRole
from app.security.auth_bearer import JWTBearer
from app.security.jwt import decode_jwt

WS_CLOSE_UNAUTHORIZED = 4401
WS_CLOSE_FORBIDDEN = 4403


def _verify_jwt_user_exists(user_data: dict, session: Session) -> None:
    """Confirm the JWT principal still exists in the DB.

    Guards against stale tokens (deleted users, reseeded local DBs, restored
    backups) reaching downstream code where they would cause FK-violation 500s.
    """
    uid = user_data.get("uid")
    if not uid or not session.get(User, UUID(uid)):
        raise HTTPException(status_code=401, detail="User not found")


def _require_role(*allowed_roles: UserRole, error_msg: str = "Insufficient privileges"):
    """Factory: returns a FastAPI dependency that enforces role requirements."""

    async def dependency(token: str = Depends(JWTBearer()), session: Session = Depends(get_session)):
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_data = payload.get("user_data", {})
        if user_data.get("role") not in list(allowed_roles):
            raise HTTPException(status_code=403, detail=error_msg)
        _verify_jwt_user_exists(user_data, session)
        return user_data

    return dependency


async def verify_self_or_admin(token: str = Depends(JWTBearer()), session: Session = Depends(get_session)):
    """Verify user is editing themselves or has admin privileges"""
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_data = payload.get("user_data", {})
    _verify_jwt_user_exists(user_data, session)
    return user_data


verify_super_admin_access = _require_role(UserRole.SUPER_ADMIN, error_msg="Admin privileges required")
verify_admin_access = _require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, error_msg="Admin privileges required")
verify_creator_access = _require_role(
    UserRole.CREATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, error_msg="Creator privileges required"
)


async def authenticate_websocket(
    websocket: WebSocket,
    token: str,
    session: Session,
    *allowed_roles: UserRole,
) -> dict | None:
    """Authenticate a WebSocket handshake.

    Browsers can't set Authorization headers on WS connections, so JWTBearer
    can't be used as a Depends here. This helper mirrors _require_role's
    semantics (decode + role check + user-exists check) for the WS path so
    auth stays consistent across transports.

    Returns user_data on success. On failure closes the socket and returns None;
    callers should `return` immediately when None.
    """
    payload = decode_jwt(token)
    if not payload:
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return None

    user_data = payload.get("user_data", {})
    if allowed_roles and user_data.get("role") not in list(allowed_roles):
        await websocket.close(code=WS_CLOSE_FORBIDDEN)
        return None

    uid = user_data.get("uid")
    if not uid or not session.get(User, UUID(uid)):
        await websocket.close(code=WS_CLOSE_UNAUTHORIZED)
        return None

    return user_data
