from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.incident_category import IncidentCategory
from app.models.incident_type import IncidentType

client = TestClient(app)


class TestCreateIncidentType:
    """Tests for POST /incident-types/ endpoint"""

    def test_create_type_admin_success(self, session, admin_auth_headers, sample_category):
        data = {
            "code": "test_coolant_failure",
            "name": "Test Coolant Failure",
            "category_id": str(sample_category.uid),
            "default_severity": 5,
        }

        response = client.post("/api/incident-types/", json=data, headers=admin_auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["code"] == "test_coolant_failure"
        assert result["name"] == "Test Coolant Failure"
        assert result["category_id"] == str(sample_category.uid)
        assert result["default_severity"] == 5
        assert "uid" in result
        assert "created" in result
        assert "updated" in result

    def test_create_type_invalid_severity_too_high(self, session, admin_auth_headers, sample_category):
        data = {
            "code": "test_bad_severity",
            "name": "Bad Severity",
            "category_id": str(sample_category.uid),
            "default_severity": 8,
        }

        response = client.post("/api/incident-types/", json=data, headers=admin_auth_headers)

        assert response.status_code == 422

    def test_create_type_invalid_severity_too_low(self, session, admin_auth_headers, sample_category):
        data = {
            "code": "test_bad_severity_low",
            "name": "Bad Severity Low",
            "category_id": str(sample_category.uid),
            "default_severity": 0,
        }

        response = client.post("/api/incident-types/", json=data, headers=admin_auth_headers)

        assert response.status_code == 422

    def test_create_type_viewer_forbidden(self, session, auth_headers, sample_category):
        data = {
            "code": "test_forbidden",
            "name": "Forbidden",
            "category_id": str(sample_category.uid),
            "default_severity": 3,
        }

        response = client.post("/api/incident-types/", json=data, headers=auth_headers)

        assert response.status_code == 403


class TestGetIncidentTypes:
    """Tests for GET /incident-types/ endpoints"""

    def test_get_all_types(self, session, auth_headers, sample_category):
        t = IncidentType(
            code="test_get_all",
            name="Test Get All",
            category_id=sample_category.uid,
            default_severity=3,
        )
        session.add(t)
        session.commit()

        response = client.get("/api/incident-types/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_types_by_category(self, session, auth_headers, sample_category):
        other_cat = IncidentCategory(code=f"other_{uuid4().hex[:8]}", name="Other")
        session.add(other_cat)
        session.commit()
        session.refresh(other_cat)

        t1 = IncidentType(
            code="test_filter_match",
            name="Match",
            category_id=sample_category.uid,
            default_severity=3,
        )
        t2 = IncidentType(
            code="test_filter_other",
            name="Other",
            category_id=other_cat.uid,
            default_severity=2,
        )
        session.add_all([t1, t2])
        session.commit()

        response = client.get(
            f"/api/incident-types/?category_id={sample_category.uid}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        codes = [t["code"] for t in data]
        assert "test_filter_match" in codes
        assert "test_filter_other" not in codes

    def test_get_type_by_uid(self, session, auth_headers, sample_category):
        t = IncidentType(
            code="test_get_one",
            name="Test Get One",
            category_id=sample_category.uid,
            default_severity=4,
        )
        session.add(t)
        session.commit()
        session.refresh(t)

        response = client.get(f"/api/incident-types/{t.uid}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == str(t.uid)
        assert data["code"] == "test_get_one"
        assert data["default_severity"] == 4

    def test_get_type_not_found(self, session, auth_headers):
        response = client.get(f"/api/incident-types/{uuid4()}", headers=auth_headers)

        assert response.status_code == 404

    def test_get_types_unauthenticated(self):
        response = client.get("/api/incident-types/")

        assert response.status_code == 403


class TestUpdateIncidentType:
    """Tests for PUT /incident-types/{uid} endpoint"""

    def test_update_type_admin_success(self, session, admin_auth_headers, sample_category):
        t = IncidentType(
            code="test_update",
            name="Before Update",
            category_id=sample_category.uid,
            default_severity=3,
        )
        session.add(t)
        session.commit()
        session.refresh(t)

        response = client.put(
            f"/api/incident-types/{t.uid}",
            json={"name": "After Update", "default_severity": 5},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "After Update"
        assert data["default_severity"] == 5
        assert data["code"] == "test_update"

    def test_update_type_viewer_forbidden(self, session, auth_headers, sample_category):
        t = IncidentType(
            code="test_update_forbidden",
            name="Forbidden",
            category_id=sample_category.uid,
            default_severity=3,
        )
        session.add(t)
        session.commit()
        session.refresh(t)

        response = client.put(
            f"/api/incident-types/{t.uid}",
            json={"name": "Nope"},
            headers=auth_headers,
        )

        assert response.status_code == 403
