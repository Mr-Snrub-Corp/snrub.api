from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.incident_category import IncidentCategory

client = TestClient(app)


class TestGetIncidentCategories:
    """Tests for GET /incident-categories/ endpoints"""

    def test_get_all_categories(self, session, auth_headers):
        """Authenticated user can list categories"""
        cat = IncidentCategory(code="test_physics", name="Test Physics")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        response = client.get("/api/incident-categories/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        codes = [c["code"] for c in data]
        assert "test_physics" in codes

    def test_get_category_by_uid(self, session, auth_headers):
        """Authenticated user can get single category by uid"""
        cat = IncidentCategory(code="test_cooling", name="Test Cooling")
        session.add(cat)
        session.commit()
        session.refresh(cat)

        response = client.get(f"/api/incident-categories/{cat.uid}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == str(cat.uid)
        assert data["code"] == "test_cooling"
        assert data["name"] == "Test Cooling"
        assert "created" in data
        assert "updated" in data

    def test_get_category_not_found(self, session, auth_headers):
        """Returns 404 for non-existent uid"""
        response = client.get(f"/api/incident-categories/{uuid4()}", headers=auth_headers)

        assert response.status_code == 404

    def test_get_categories_unauthenticated(self):
        """Unauthenticated user cannot list categories"""
        response = client.get("/api/incident-categories/")

        assert response.status_code == 403
