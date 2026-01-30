from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_login_success(authenticated_user, test_user_data):
    """Test successful login with valid credentials"""
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"],  # Plain password
    }

    response = client.post("/api/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == test_user_data["email"]


def test_login_invalid_credentials(authenticated_user, test_user_data):
    """Test login with invalid password"""
    login_data = {"email": test_user_data["email"], "password": "WrongPassword123!"}

    response = client.post("/api/auth/login", json=login_data)

    assert response.status_code == 401
