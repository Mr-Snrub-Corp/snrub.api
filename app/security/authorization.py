from fastapi import Depends, HTTPException

from app.models.user import UserRole
from app.security.auth_bearer import JWTBearer
from app.security.jwt import decode_jwt


def _require_role(*allowed_roles: UserRole, error_msg: str = "Insufficient privileges"):
    """Factory: returns a FastAPI dependency that enforces role requirements."""

    async def dependency(token: str = Depends(JWTBearer())):
        payload = decode_jwt(token)
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid token")
        user_data = payload.get("user_data", {})
        if user_data.get("role") not in list(allowed_roles):
            raise HTTPException(status_code=403, detail=error_msg)
        return user_data

    return dependency


async def verify_self_or_admin(token: str = Depends(JWTBearer())):
    """Verify user is editing themselves or has admin privileges"""
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload.get("user_data", {})


verify_super_admin_access = _require_role(UserRole.SUPER_ADMIN, error_msg="Admin privileges required")
verify_admin_access = _require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN, error_msg="Admin privileges required")
verify_creator_access = _require_role(
    UserRole.CREATOR, UserRole.ADMIN, UserRole.SUPER_ADMIN, error_msg="Creator privileges required"
)
