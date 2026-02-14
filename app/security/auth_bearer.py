import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.security.jwt import decode_jwt


class JWTBearer(HTTPBearer):
    """Validate JWT token in the Authorization header"""

    # enabled automatic error reporting
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if credentials:
            if not credentials.scheme == "Bearer":
                raise HTTPException(status_code=401, detail="Invalid authentication scheme.")
            if not self.verify_jwt(credentials.credentials):
                raise HTTPException(status_code=401, detail="Invalid token or expired token.")
            return credentials.credentials
        else:
            raise HTTPException(status_code=401, detail="Invalid authorization code.")

    def verify_jwt(self, jwtoken: str) -> bool:
        """Verify the JWT token"""
        is_token_valid: bool = False

        try:
            payload = decode_jwt(jwtoken)
        except (jwt.PyJWTError, jwt.ExpiredSignatureError, KeyError):
            payload = None
        if payload:
            is_token_valid = True

        return is_token_valid


# __call__ (notes)
# In the __call__ method, we defined a variable called credentials of type HTTPAuthorizationCredentials,
# which is created when the JWTBearer class is invoked.
# We then proceeded to check if the credentials passed in during the course of invoking the class are valid:

# If the credential scheme isn't a bearer scheme, we raised an exception for an invalid token scheme.
# If a bearer token was passed, we verified that the JWT is valid.
# If no credentials were received, we raised an invalid authorization error.
