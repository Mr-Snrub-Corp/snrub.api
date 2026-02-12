from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.incident_report_subject import IncidentReportSubject, SubjectRole

client = TestClient(app)


class TestAddSubject:
    """Tests for POST /incident-reports/{report_id}/subjects/ endpoint"""

    def test_add_subject_admin_success(self, session, admin_auth_headers, sample_report, authenticated_user):
        data = {
            "user_id": str(authenticated_user.uid),
            "role": "responsible",
        }

        response = client.post(
            f"/api/incident-reports/{sample_report.uid}/subjects/", json=data, headers=admin_auth_headers
        )

        assert response.status_code == 200
        result = response.json()
        assert result["user_id"] == str(authenticated_user.uid)
        assert result["incident_report_id"] == str(sample_report.uid)
        assert result["role"] == "responsible"
        assert "uid" in result
        assert "created" in result

    def test_add_subject_involved_role(self, session, admin_auth_headers, sample_report, authenticated_user):
        data = {
            "user_id": str(authenticated_user.uid),
            "role": "involved",
        }

        response = client.post(
            f"/api/incident-reports/{sample_report.uid}/subjects/", json=data, headers=admin_auth_headers
        )

        assert response.status_code == 200
        assert response.json()["role"] == "involved"

    def test_add_subject_witness_role(self, session, admin_auth_headers, sample_report, authenticated_user):
        data = {
            "user_id": str(authenticated_user.uid),
            "role": "witness",
        }

        response = client.post(
            f"/api/incident-reports/{sample_report.uid}/subjects/", json=data, headers=admin_auth_headers
        )

        assert response.status_code == 200
        assert response.json()["role"] == "witness"

    def test_add_subject_viewer_forbidden(self, session, auth_headers, sample_report, authenticated_user):
        data = {
            "user_id": str(authenticated_user.uid),
            "role": "responsible",
        }

        response = client.post(
            f"/api/incident-reports/{sample_report.uid}/subjects/", json=data, headers=auth_headers
        )

        assert response.status_code == 403

    def test_add_subject_unauthenticated(self, session, sample_report, authenticated_user):
        data = {
            "user_id": str(authenticated_user.uid),
            "role": "responsible",
        }

        response = client.post(f"/api/incident-reports/{sample_report.uid}/subjects/", json=data)

        assert response.status_code == 403

    def test_add_subject_report_not_found(self, session, admin_auth_headers, authenticated_user):
        data = {
            "user_id": str(authenticated_user.uid),
            "role": "responsible",
        }

        response = client.post(
            f"/api/incident-reports/{uuid4()}/subjects/", json=data, headers=admin_auth_headers
        )

        assert response.status_code == 404


class TestGetSubjects:
    """Tests for GET /incident-reports/{report_id}/subjects/ endpoint"""

    def test_get_subjects_for_report(self, session, auth_headers, sample_report, creator_user):
        subject = IncidentReportSubject(
            incident_report_id=sample_report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.WITNESS,
        )
        session.add(subject)
        session.commit()

        response = client.get(f"/api/incident-reports/{sample_report.uid}/subjects/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["user_id"] == str(creator_user.uid)
        assert data[0]["role"] == "witness"

    def test_get_subjects_empty_list(self, session, auth_headers, sample_report):
        response = client.get(f"/api/incident-reports/{sample_report.uid}/subjects/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_subjects_unauthenticated(self, session, sample_report):
        response = client.get(f"/api/incident-reports/{sample_report.uid}/subjects/")

        assert response.status_code == 403


class TestRemoveSubject:
    """Tests for DELETE /incident-reports/{report_id}/subjects/{subject_uid} endpoint"""

    def test_remove_subject_admin_success(self, session, admin_auth_headers, sample_report, creator_user):
        subject = IncidentReportSubject(
            incident_report_id=sample_report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.INVOLVED,
        )
        session.add(subject)
        session.commit()
        session.refresh(subject)

        response = client.delete(
            f"/api/incident-reports/{sample_report.uid}/subjects/{subject.uid}", headers=admin_auth_headers
        )

        assert response.status_code == 200

    def test_remove_subject_viewer_forbidden(self, session, auth_headers, sample_report, creator_user):
        subject = IncidentReportSubject(
            incident_report_id=sample_report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.INVOLVED,
        )
        session.add(subject)
        session.commit()
        session.refresh(subject)

        response = client.delete(
            f"/api/incident-reports/{sample_report.uid}/subjects/{subject.uid}", headers=auth_headers
        )

        assert response.status_code == 403

    def test_remove_subject_not_found(self, session, admin_auth_headers, sample_report):
        response = client.delete(
            f"/api/incident-reports/{sample_report.uid}/subjects/{uuid4()}", headers=admin_auth_headers
        )

        assert response.status_code == 404


class TestCascadeDelete:
    """Tests that deleting an incident report cascades to subjects"""

    def test_delete_report_cascades_subjects(self, session, admin_auth_headers, sample_report, creator_user):
        subject = IncidentReportSubject(
            incident_report_id=sample_report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.RESPONSIBLE,
        )
        session.add(subject)
        session.commit()
        session.refresh(subject)
        subject_uid = subject.uid

        # Delete the report
        response = client.delete(f"/api/incident-reports/{sample_report.uid}", headers=admin_auth_headers)
        assert response.status_code == 200

        # Verify subject is gone
        from sqlmodel import select

        result = session.exec(
            select(IncidentReportSubject).where(IncidentReportSubject.uid == subject_uid)
        ).first()
        assert result is None
