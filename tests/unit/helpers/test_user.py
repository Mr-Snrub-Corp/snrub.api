import pytest
from pydantic import SecretStr

from app.models.user import validate_password_strength


def test_validate_password_strength():
    # Test valid password

    valid_password = SecretStr("StrongP@ss123")
    assert validate_password_strength(valid_password) == valid_password

    # Test invalid passwords
    invalid_cases = [
        ("Short1@", "Password must be at least 8 characters long"),
        ("nouppercase123!", "Password must contain at least one uppercase letter"),
        ("NOLOWERCASE123!", "Password must contain at least one lowercase letter"),
        ("NoDigitsHere!", "Password must contain at least one digit"),
        ("NoSpecial123", "Password must contain at least one special character"),
    ]

    for password, expected_error in invalid_cases:
        with pytest.raises(ValueError, match=expected_error):
            validate_password_strength(SecretStr(password))

    # Test None case
    assert validate_password_strength(None) is None


# docker compose exec api pytest tests/unit/models/test_user.py -v
