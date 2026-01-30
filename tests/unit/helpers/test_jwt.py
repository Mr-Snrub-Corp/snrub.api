import time
from uuid import uuid4

import jwt
from mimesis import Person

from app.core.config import settings
from app.security.jwt import decode_jwt, sign_jwt


def test_sign_jwt(): # add caplog param for logging
    # caplog.set_level(logging.INFO)
    user = Person()
    # Generate a UUID using Python's uuid module
    user_uid = uuid4()

    user_data = {
        "uid": str(user_uid),
        "email": user.email(),
        "name": user.name(),
        "role": "VIEWER"
    }

    token = sign_jwt(user_data["uid"], user_data)

    assert token.access_token
    assert token.user == user_data

        # Decode the token manually to verify its contents
    decoded = jwt.decode(
        token.access_token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM]
    )

    # Verify token payload
    assert decoded["user_uid"] == str(user_uid), "Token should contain user UID"
    assert decoded["user_data"] == user_data, "Token should contain user data"
    assert "expires" in decoded, "Token should have expiration"
    assert decoded["expires"] > time.time(), "Token should not be expired"

def test_decode_jwt():

    user_uid = uuid4()
    user_data = {"uid": str(user_uid), "name": "Homer Simpson", "email": "chunkylover53@aol.com", "role": "VIEWER"}

    # Generate a token
    token_response = sign_jwt(user_uid, user_data)
    token = token_response.access_token

    # Test successful decoding
    decoded = decode_jwt(token)
    assert decoded is not None, "Valid token should be decoded successfully"
    assert decoded["user_uid"] == str(user_uid), "Decoded token should contain user UID"

    # Test expired token
    payload = {
        "user_uid": str(user_uid),
        "user_data": user_data,
        "expires": time.time() - 100  # Expired 100 seconds ago
    }
    expired_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    assert decode_jwt(expired_token) is None, "Expired token should return None"
