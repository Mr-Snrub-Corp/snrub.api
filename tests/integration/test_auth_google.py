"""Tests for the Google OAuth callback.

Only the token exchange is stubbed -- `authorize_access_token` is the one call
that would hit Google's network endpoints. Everything downstream of it (user
lookup, auto-provisioning, role assignment, JWT signing, session write) is the
real code path.

The two active tests cover the auto-provisioning invariants, because that is
where this route carries security weight: an external login decides what role a
brand new account gets, and must not alter an existing account's role.
"""

import pytest
from fastapi.testclient import TestClient
from mimesis import Person
from sqlmodel import select

from app.main import app
from app.models.user import User, UserRole
from app.security import oauth_client

client = TestClient(app)

CALLBACK = "/api/auth/google/callback"


@pytest.fixture
def google_returns(monkeypatch):
    """Stub the token exchange. Returns a setter for the userinfo Google would send."""

    def _set(email: str, name: str = "Google Person") -> None:
        async def fake_authorize_access_token(request):  # noqa: ARG001
            return {"userinfo": {"email": email, "name": name}}

        monkeypatch.setattr(oauth_client.oauth.google, "authorize_access_token", fake_authorize_access_token)

    return _set


class TestCallbackProvisioning:
    def test_callback_provisions_unknown_email_as_viewer(self, session, google_returns):
        """A first-time Google login creates the user at the lowest role."""
        email = Person().email()
        google_returns(email, name="Brand New")

        response = client.get(CALLBACK, follow_redirects=False)

        assert response.status_code == 307
        assert "success=true" in response.headers["location"]

        user = session.exec(select(User).where(User.email == email)).first()
        assert user is not None
        assert user.name == "Brand New"
        # The security property: an external identity provider must never be able
        # to mint anything above VIEWER.
        assert user.role == UserRole.VIEWER
        # OAuth users get no usable password, so local login cannot be attempted.
        assert user.password == ""

    def test_callback_reuses_existing_user_and_preserves_role(self, session, admin_user, google_returns):
        """An existing account is matched by email, not duplicated or re-roled."""
        google_returns(admin_user.email, name="Renamed By Google")

        response = client.get(CALLBACK, follow_redirects=False)

        assert response.status_code == 307
        assert "success=true" in response.headers["location"]

        rows = session.exec(select(User).where(User.email == admin_user.email)).all()
        assert len(rows) == 1
        assert rows[0].uid == admin_user.uid
        # Signing in via Google must not downgrade an admin...
        assert rows[0].role == UserRole.ADMIN
        # ...nor overwrite the stored profile with Google's copy.
        assert rows[0].name == admin_user.name


# ---------------------------------------------------------------------------
# Left for you to implement.
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="TODO: OAuthError branch -- google.py lines 33-39")
def test_callback_oauth_error_redirects_with_failure(session, monkeypatch):
    """A failed token exchange should redirect with success=false, not 500.

    Make the stub raise `authlib.integrations.starlette_client.OAuthError`
    instead of returning a payload, then assert the redirect Location contains
    `success=false` and `error=auth_failed`, and that no User row was created.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="TODO: /token happy path -- google.py lines 70-71, 74")
def test_token_returns_jwt_and_clears_session(session, google_returns):
    """GET /token should hand back the JWT the callback stashed, exactly once.

    Call the callback first so the session cookie is set, then GET
    /api/auth/google/token on the same client. Assert the response carries an
    access_token plus the user payload, and that an immediate second call now
    returns 401 -- the values are popped, so the token is single-use.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="TODO: /token auth-bypass guard -- google.py lines 72-73")
def test_token_without_pending_auth_returns_401(session):
    """GET /token with no prior callback must be rejected.

    Use a fresh TestClient so no session cookie is present. This is the guard
    stopping anyone from pulling a token straight out of the endpoint, so it is
    worth pinning even though it is a two-line branch.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="TODO: /login redirect -- google.py lines 25-26")
def test_login_redirects_to_google_consent(session):
    """GET /login should 302 to accounts.google.com with the configured redirect_uri.

    `authorize_redirect` fetches Google's OpenID metadata document, so either
    stub `oauth.google.load_server_metadata` or stub `authorize_redirect` itself
    and assert it was handed `settings.GOOGLE_AUTH_REDIRECT_URI`.
    """
    raise NotImplementedError
