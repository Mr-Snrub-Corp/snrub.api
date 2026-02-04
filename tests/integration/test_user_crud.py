from fastapi.testclient import TestClient
from mimesis import Person
from sqlmodel import select

from app.main import app
from app.models.user import User

client = TestClient(app)


class TestCreateUser:
    """Tests for POST /users/ endpoint"""

    def test_create_user_admin_success(self, session, admin_auth_headers):
        """Admin can create a user with valid data"""
        person = Person()
        new_user_data = {
            "email": person.email(),
            "name": person.full_name(),
            "role": "viewer",
            "password": "NewUser123!",
        }

        response = client.post("/api/users/", json=new_user_data, headers=admin_auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response contains expected fields
        assert data["email"] == new_user_data["email"]
        assert data["name"] == new_user_data["name"]
        assert data["role"] == new_user_data["role"]
        assert "uid" in data
        assert "created" in data
        assert "updated" in data

        # Verify password is not exposed in response
        assert "password" not in data

        # Verify user exists in database
        statement = select(User).where(User.email == new_user_data["email"])
        db_user = session.exec(statement).first()
        assert db_user is not None
        assert db_user.email == new_user_data["email"]

    def test_create_user_non_admin_forbidden(self, authenticated_user, auth_headers):
        """Non-admin user cannot create users"""
        person = Person()
        new_user_data = {
            "email": person.email(),
            "name": person.full_name(),
            "role": "viewer",
            "password": "NewUser123!",
        }

        response = client.post("/api/users/", json=new_user_data, headers=auth_headers)

        assert response.status_code == 403


class TestGetUser:
    """Tests for GET /users/{uid} endpoint"""

    def test_get_user_by_uid_success(self, authenticated_user, auth_headers):
        """Authenticated user can retrieve a user by UID"""
        response = client.get(f"/api/users/{authenticated_user.uid}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Verify response contains expected user data
        assert data["uid"] == str(authenticated_user.uid)
        assert data["email"] == authenticated_user.email
        assert data["name"] == authenticated_user.name
        assert data["role"] == authenticated_user.role

        # Verify password is not exposed in response
        assert "password" not in data


class TestUpdateUser:
    """Tests for PUT /users/{uid} endpoint"""

    def test_update_user_partial_update(self, authenticated_user, auth_headers):
        """Authenticated user can update specific fields only"""
        original_email = authenticated_user.email
        original_role = authenticated_user.role
        new_name = "Updated Name"

        update_data = {"name": new_name}

        response = client.put(
            f"/api/users/{authenticated_user.uid}",
            json=update_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify only name was updated
        assert data["name"] == new_name

        # Verify other fields remain unchanged
        assert data["email"] == original_email
        assert data["role"] == original_role


class TestDeleteUser:
    """Tests for DELETE /users/{uid} endpoint"""

    def test_delete_user_admin_success(self, session, authenticated_user, admin_auth_headers):
        """Admin can delete a user"""
        user_uid = authenticated_user.uid

        response = client.delete(f"/api/users/{user_uid}", headers=admin_auth_headers)

        assert response.status_code == 200

        # Verify user no longer exists in database
        statement = select(User).where(User.uid == user_uid)
        db_user = session.exec(statement).first()
        assert db_user is None

    def test_delete_user_non_admin_forbidden(self, authenticated_user, auth_headers):
        """Non-admin user cannot delete users"""
        response = client.delete(f"/api/users/{authenticated_user.uid}", headers=auth_headers)

        assert response.status_code == 403


class TestUserPhoto:
    """Tests for user photo upload/retrieve endpoints"""

    def test_upload_photo_unauthenticated(self, authenticated_user, sample_png_bytes):
        """Unauthenticated user cannot upload photo"""
        files = {"file": ("photo.png", sample_png_bytes, "image/png")}

        response = client.put(
            f"/api/users/{authenticated_user.uid}/photo",
            files=files,
        )

        assert response.status_code == 403

    def test_upload_photo_success(self, authenticated_user, admin_auth_headers, sample_png_bytes):
        """User can upload a PNG photo"""
        files = {"file": ("photo.png", sample_png_bytes, "image/png")}

        response = client.put(
            f"/api/users/{authenticated_user.uid}/photo",
            files=files,
            headers=admin_auth_headers,
        )

        assert response.status_code == 200

    def test_upload_photo_invalid_mime_type(self, authenticated_user, admin_auth_headers):
        """Uploading non-PNG file should fail"""
        files = {"file": ("photo.jpg", b"fake jpeg data", "image/jpeg")}

        response = client.put(
            f"/api/users/{authenticated_user.uid}/photo",
            files=files,
            headers=admin_auth_headers,
        )

        assert response.status_code == 400

    # def test_get_photo_success(self, user_with_photo, user_with_photo_auth_headers, sample_png_bytes):
    #     """User can retrieve their photo"""
    #     response = client.get(
    #         f"/api/users/{user_with_photo.uid}/photo",
    #         headers=user_with_photo_auth_headers,
    #     )

    #     assert response.status_code == 200
    #     assert response.headers["content-type"] == "image/png"
    #     assert response.content == sample_png_bytes

    # def test_get_photo_not_found(self, authenticated_user, auth_headers):
    #     """Getting photo for user without photo returns 404"""
    #     response = client.get(
    #         f"/api/users/{authenticated_user.uid}/photo",
    #         headers=auth_headers,
    #     )

    #     assert response.status_code == 404

    def test_delete_photo_success(self, session, user_with_photo, admin_auth_headers):
        """Admin can delete a user's photo"""
        response = client.delete(
            f"/api/users/{user_with_photo.uid}/photo",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200

        # Verify photo is removed from database
        session.refresh(user_with_photo)
        assert user_with_photo.photo is None
