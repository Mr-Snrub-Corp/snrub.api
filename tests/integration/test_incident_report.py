from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.incident_report import EscalationLevel, IncidentReport, IncidentStatus

client = TestClient(app)


class TestCreateIncidentReport:
    """Tests for POST /incident-reports/ endpoint"""

    def test_create_report_creator_success(self, session, creator_auth_headers, creator_user, sample_type):
        data = {
            "incident_type_id": str(sample_type.uid),
            "description": "Coolant pressure dropping in sector 7-G",
            "severity": 5,
            "occurred_at": "2026-04-26T01:23:00",
        }

        response = client.post("/api/incident-reports/", json=data, headers=creator_auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["incident_type_id"] == str(sample_type.uid)
        assert result["severity"] == 5
        assert result["status"] == "reported"
        assert result["escalation_level"] == "none"
        assert result["reported_by_user_id"] == str(creator_user.uid)
        assert result["description"] == "Coolant pressure dropping in sector 7-G"
        assert "uid" in result
        assert "created" in result

    def test_create_report_admin_success(self, session, admin_auth_headers, admin_user, sample_type):
        data = {
            "incident_type_id": str(sample_type.uid),
            "severity": 3,
            "occurred_at": "2026-04-26T01:23:00",
        }

        response = client.post("/api/incident-reports/", json=data, headers=admin_auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert result["reported_by_user_id"] == str(admin_user.uid)

    def test_create_report_viewer_forbidden(self, session, auth_headers, sample_type):
        data = {
            "incident_type_id": str(sample_type.uid),
            "severity": 3,
            "occurred_at": "2026-04-26T01:23:00",
        }

        response = client.post("/api/incident-reports/", json=data, headers=auth_headers)

        assert response.status_code == 403

    def test_create_report_invalid_severity(self, session, creator_auth_headers, sample_type):
        data = {
            "incident_type_id": str(sample_type.uid),
            "severity": 0,
            "occurred_at": "2026-04-26T01:23:00",
        }

        response = client.post("/api/incident-reports/", json=data, headers=creator_auth_headers)

        assert response.status_code == 422

    def test_create_report_unauthenticated(self, session, sample_type):
        data = {
            "incident_type_id": str(sample_type.uid),
            "severity": 3,
            "occurred_at": "2026-04-26T01:23:00",
        }

        response = client.post("/api/incident-reports/", json=data)

        assert response.status_code == 403


class TestGetIncidentReports:
    """Tests for GET /incident-reports/ endpoints"""

    def test_get_all_reports(self, session, auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=4,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()

        response = client.get("/api/incident-reports/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_get_report_by_uid(self, session, auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=5,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        response = client.get(f"/api/incident-reports/{report.uid}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == str(report.uid)
        assert data["severity"] == 5

    def test_get_report_not_found(self, session, auth_headers):
        response = client.get(f"/api/incident-reports/{uuid4()}", headers=auth_headers)

        assert response.status_code == 404

    def test_get_reports_unauthenticated(self):
        response = client.get("/api/incident-reports/")

        assert response.status_code == 403


class TestUpdateIncidentReport:
    """Tests for PUT /incident-reports/{uid} endpoint"""

    def test_update_status_admin_success(self, session, admin_auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=4,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"status": "confirmed"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"

    def test_update_escalation_admin_success(self, session, admin_auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=6,
            status=IncidentStatus.CONFIRMED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"escalation_level": "escalated"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["escalation_level"] == "escalated"
        assert data["status"] == "confirmed"

    def test_update_report_creator_forbidden(self, session, creator_auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=3,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"status": "confirmed"},
            headers=creator_auth_headers,
        )

        assert response.status_code == 403

    def test_update_report_viewer_forbidden(self, session, auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=3,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"status": "confirmed"},
            headers=auth_headers,
        )

        assert response.status_code == 403


class TestDeleteIncidentReport:
    """Tests for DELETE /incident-reports/{uid} endpoint"""

    def test_delete_report_admin_success(self, session, admin_auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=3,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        report_uid = report.uid

        response = client.delete(f"/api/incident-reports/{report_uid}", headers=admin_auth_headers)

        assert response.status_code == 200

    def test_delete_report_non_admin_forbidden(self, session, auth_headers, sample_type, creator_user):
        report = IncidentReport(
            incident_type_id=sample_type.uid,
            severity=3,
            status=IncidentStatus.REPORTED,
            escalation_level=EscalationLevel.NONE,
            reported_by_user_id=creator_user.uid,
            occurred_at=datetime.utcnow(),
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        response = client.delete(f"/api/incident-reports/{report.uid}", headers=auth_headers)

        assert response.status_code == 403
