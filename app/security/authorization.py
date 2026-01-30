from fastapi import Depends, HTTPException

from app.models.user import UserRole
from app.security.auth_bearer import JWTBearer
from app.security.jwt import decode_jwt


async def verify_super_admin_access(token: str = Depends(JWTBearer())):
    """Verify user has admin privileges"""
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = payload.get("user_data", {})
    user_role = user_data.get("role")

    # Check if user has admin or super admin role
    if user_role not in [UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return user_data


async def verify_admin_access(token: str = Depends(JWTBearer())):
    """Verify user has creator privileges or higher"""
    payload = decode_jwt(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_data = payload.get("user_data", {})
    user_role = user_data.get("role")

    if user_role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Creator privileges required")

    return user_data
