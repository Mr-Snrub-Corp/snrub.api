"""Integration tests for password reset flow."""

from datetime import datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlmodel import select

from app.controllers.user import pwd_context
from app.main import app
from app.models.password_reset import PasswordReset

client = TestClient(app)


class TestRequestPasswordReset:
    """Tests for POST /api/auth/request-password-reset endpoint."""

    def test_request_reset_valid_email_returns_success(self, session, authenticated_user):
        """Request password reset for valid email returns success message."""
        response = client.post(
            "/api/auth/request-password-reset",
            json={"email": authenticated_user.email},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "If your email is registered, you will receive a password reset link"

    def test_request_reset_valid_email_creates_token(self, session, authenticated_user):
        """Request password reset for valid email creates token in database."""
        response = client.post(
            "/api/auth/request-password-reset",
            json={"email": authenticated_user.email},
        )

        assert response.status_code == 200

        # Verify token was created in database
        statement = select(PasswordReset).where(PasswordReset.user_id == authenticated_user.uid)
        token = session.exec(statement).first()

        assert token is not None
        assert token.used is False
        assert token.expires_at > datetime.utcnow()

    def test_request_reset_invalid_email_returns_same_message(self, session):
        """Request password reset for non-existent email returns same success message.

        This prevents email enumeration attacks.
        """
        response = client.post(
            "/api/auth/request-password-reset",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        # Same message as valid email to prevent enumeration
        assert data["message"] == "If your email is registered, you will receive a password reset link"

    def test_request_reset_invalidates_previous_tokens(self, session, authenticated_user):
        """Requesting a new reset token invalidates previous unused tokens."""
        # Create an existing token
        existing_token = PasswordReset.create_token(authenticated_user.uid)
        session.add(existing_token)
        session.commit()
        token_id = existing_token.token  # Save the token ID for re-query

        # Request a new token
        response = client.post(
            "/api/auth/request-password-reset",
            json={"email": authenticated_user.email},
        )

        assert response.status_code == 200

        # Re-query the token from DB (since it was modified by a different session)
        session.expire_all()
        statement = select(PasswordReset).where(PasswordReset.token == token_id)
        updated_token = session.exec(statement).first()

        # Previous token should be marked as used
        assert updated_token is not None
        assert updated_token.used is True


class TestPerformPasswordReset:
    """Tests for POST /api/auth/reset-password endpoint."""

    def test_reset_password_valid_token_succeeds(self, session, authenticated_user, test_user_data):
        """Password reset with valid token succeeds."""
        # Create a valid token
        token = PasswordReset.create_token(authenticated_user.uid)
        session.add(token)
        session.commit()

        new_password = "NewSecurePass123!"

        response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": new_password},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Password reset successfully"

    def test_reset_password_can_login_with_new_password(self, session, authenticated_user, test_user_data):
        """After password reset, user can login with new password."""
        # Create a valid token
        token = PasswordReset.create_token(authenticated_user.uid)
        session.add(token)
        session.commit()

        new_password = "NewSecurePass123!"

        # Reset the password
        reset_response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": new_password},
        )
        assert reset_response.status_code == 200

        # Try to login with new password
        login_response = client.post(
            "/api/auth/login",
            json={"email": authenticated_user.email, "password": new_password},
        )

        assert login_response.status_code == 200
        assert "access_token" in login_response.json()

    def test_reset_password_old_password_no_longer_works(self, session, authenticated_user, test_user_data):
        """After password reset, old password no longer works."""
        # Create a valid token
        token = PasswordReset.create_token(authenticated_user.uid)
        session.add(token)
        session.commit()

        new_password = "NewSecurePass123!"
        old_password = test_user_data["password"]

        # Reset the password
        reset_response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": new_password},
        )
        assert reset_response.status_code == 200

        # Try to login with old password
        login_response = client.post(
            "/api/auth/login",
            json={"email": authenticated_user.email, "password": old_password},
        )

        assert login_response.status_code == 401

    def test_reset_password_expired_token_fails(self, session, authenticated_user):
        """Password reset with expired token fails."""
        # Create an expired token
        token = PasswordReset(
            user_id=authenticated_user.uid,
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired 1 hour ago
        )
        session.add(token)
        session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": "NewPass123!"},
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    def test_reset_password_used_token_fails(self, session, authenticated_user):
        """Password reset with already-used token fails."""
        # Create a used token
        token = PasswordReset.create_token(authenticated_user.uid)
        token.used = True
        session.add(token)
        session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": "NewPass123!"},
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower() or "used" in response.json()["detail"].lower()

    def test_reset_password_invalid_token_fails(self, session):
        """Password reset with non-existent token fails."""
        fake_token = uuid4()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": str(fake_token), "new_password": "NewPass123!"},
        )

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_reset_password_marks_token_as_used(self, session, authenticated_user):
        """After successful password reset, token is marked as used."""
        # Create a valid token
        token = PasswordReset.create_token(authenticated_user.uid)
        session.add(token)
        session.commit()

        response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": "NewPass123!"},
        )

        assert response.status_code == 200

        # Refresh token from DB
        session.refresh(token)
        assert token.used is True

    def test_reset_password_token_cannot_be_reused(self, session, authenticated_user):
        """Token cannot be used twice for password reset."""
        # Create a valid token
        token = PasswordReset.create_token(authenticated_user.uid)
        session.add(token)
        session.commit()

        # First reset should succeed
        first_response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": "FirstNewPass123!"},
        )
        assert first_response.status_code == 200

        # Second reset with same token should fail
        second_response = client.post(
            "/api/auth/reset-password",
            json={"token": str(token.token), "new_password": "SecondNewPass123!"},
        )
        assert second_response.status_code == 400
