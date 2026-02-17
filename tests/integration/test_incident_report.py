from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.incident_report import EscalationLevel, IncidentReport, IncidentStatus
from app.models.incident_report_subject import IncidentReportSubject, SubjectRole

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
        assert result["subjects"] == []
        assert "uid" in result
        assert "created" in result

    def test_create_report_with_subjects(
        self, session, creator_auth_headers, creator_user, sample_type, authenticated_user
    ):
        data = {
            "incident_type_id": str(sample_type.uid),
            "description": "Operator found sleeping at console",
            "severity": 4,
            "occurred_at": "2026-04-26T01:23:00",
            "subjects": [
                {"user_id": str(authenticated_user.uid), "role": "responsible"},
                {"user_id": str(creator_user.uid), "role": "witness"},
            ],
        }

        response = client.post("/api/incident-reports/", json=data, headers=creator_auth_headers)

        assert response.status_code == 200
        result = response.json()
        assert len(result["subjects"]) == 2
        subject_roles = {s["role"] for s in result["subjects"]}
        assert subject_roles == {"responsible", "witness"}
        subject_user_ids = {s["user_id"] for s in result["subjects"]}
        assert str(authenticated_user.uid) in subject_user_ids
        assert str(creator_user.uid) in subject_user_ids

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
        assert result["subjects"] == []

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

    def test_get_all_reports_includes_subjects(self, session, auth_headers, sample_type, creator_user):
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

        subject = IncidentReportSubject(
            incident_report_id=report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.WITNESS,
        )
        session.add(subject)
        session.commit()

        response = client.get("/api/incident-reports/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        report_data = next(r for r in data if r["uid"] == str(report.uid))
        assert len(report_data["subjects"]) == 1
        assert report_data["subjects"][0]["role"] == "witness"

    def test_get_report_by_uid_includes_subjects(self, session, auth_headers, sample_type, creator_user):
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

        subject = IncidentReportSubject(
            incident_report_id=report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.RESPONSIBLE,
        )
        session.add(subject)
        session.commit()

        response = client.get(f"/api/incident-reports/{report.uid}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == str(report.uid)
        assert data["severity"] == 5
        assert len(data["subjects"]) == 1
        assert data["subjects"][0]["user_id"] == str(creator_user.uid)

    def test_get_report_empty_subjects(self, session, auth_headers, sample_type, creator_user):
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

        response = client.get(f"/api/incident-reports/{report.uid}", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["subjects"] == []

    def test_get_all_no_query_params(self, session, auth_headers, sample_type, creator_user):
        reports = []
        for i in range(3):
            report = IncidentReport(
                incident_type_id=sample_type.uid,
                severity=i + 1,
                status=IncidentStatus.REPORTED,
                escalation_level=EscalationLevel.NONE,
                reported_by_user_id=creator_user.uid,
                occurred_at=datetime.utcnow(),
            )
            session.add(report)
            reports.append(report)
        session.commit()

        response = client.get("/api/incident-reports/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        returned_uids = {r["uid"] for r in data}
        for r in reports:
            assert str(r.uid) in returned_uids

    def test_get_all_with_offset(self, session, auth_headers, sample_type, creator_user):
        reports = []
        for i in range(5):
            report = IncidentReport(
                incident_type_id=sample_type.uid,
                severity=3,
                status=IncidentStatus.REPORTED,
                escalation_level=EscalationLevel.NONE,
                reported_by_user_id=creator_user.uid,
                occurred_at=datetime.utcnow(),
            )
            session.add(report)
            reports.append(report)
        session.commit()

        all_response = client.get("/api/incident-reports/", headers=auth_headers)
        all_data = all_response.json()

        offset_response = client.get("/api/incident-reports/?offset=2", headers=auth_headers)
        offset_data = offset_response.json()

        assert offset_response.status_code == 200
        assert len(offset_data) == len(all_data) - 2

    def test_get_all_with_limit(self, session, auth_headers, sample_type, creator_user):
        for i in range(5):
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

        response = client.get("/api/incident-reports/?limit=2", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_all_filter_by_status(self, session, auth_headers, sample_type, creator_user):
        statuses = [IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.REPORTED, IncidentStatus.CONFIRMED]
        for s in statuses:
            report = IncidentReport(
                incident_type_id=sample_type.uid,
                severity=3,
                status=s,
                escalation_level=EscalationLevel.NONE,
                reported_by_user_id=creator_user.uid,
                occurred_at=datetime.utcnow(),
            )
            session.add(report)
        session.commit()

        response = client.get("/api/incident-reports/?status=resolved&status=closed", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        returned_statuses = {r["status"] for r in data}
        assert returned_statuses <= {"resolved", "closed"}
        assert len(data) >= 2

    def test_get_report_not_found(self, session, auth_headers):
        response = client.get(f"/api/incident-reports/{uuid4()}", headers=auth_headers)

        assert response.status_code == 404

    def test_get_reports_unauthenticated(self):
        response = client.get("/api/incident-reports/")

        assert response.status_code == 403


class TestFilterByDateRange:
    """Tests for date_from/date_to filtering on GET /incident-reports/"""

    def _create_reports(self, session, sample_type, creator_user):
        dates = [datetime(2025, 1, 1), datetime(2025, 2, 1), datetime(2025, 3, 1)]
        reports = []
        for d in dates:
            report = IncidentReport(
                incident_type_id=sample_type.uid,
                severity=3,
                status=IncidentStatus.REPORTED,
                escalation_level=EscalationLevel.NONE,
                reported_by_user_id=creator_user.uid,
                occurred_at=d,
            )
            session.add(report)
            reports.append(report)
        session.commit()
        return reports

    def test_filter_date_from_only(self, session, auth_headers, sample_type, creator_user):
        reports = self._create_reports(session, sample_type, creator_user)
        response = client.get("/api/incident-reports/?date_from=2025-01-15T00:00:00", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        returned_uids = {r["uid"] for r in data}
        assert str(reports[0].uid) not in returned_uids
        assert str(reports[1].uid) in returned_uids
        assert str(reports[2].uid) in returned_uids

    def test_filter_date_to_only(self, session, auth_headers, sample_type, creator_user):
        reports = self._create_reports(session, sample_type, creator_user)
        response = client.get("/api/incident-reports/?date_to=2025-02-15T00:00:00", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        returned_uids = {r["uid"] for r in data}
        assert str(reports[0].uid) in returned_uids
        assert str(reports[1].uid) in returned_uids
        assert str(reports[2].uid) not in returned_uids

    def test_filter_date_range(self, session, auth_headers, sample_type, creator_user):
        reports = self._create_reports(session, sample_type, creator_user)
        response = client.get(
            "/api/incident-reports/?date_from=2025-01-15T00:00:00&date_to=2025-02-15T00:00:00", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        returned_uids = {r["uid"] for r in data}
        assert str(reports[0].uid) not in returned_uids
        assert str(reports[1].uid) in returned_uids
        assert str(reports[2].uid) not in returned_uids

    def test_filter_date_range_no_results(self, session, auth_headers, sample_type, creator_user):
        self._create_reports(session, sample_type, creator_user)
        response = client.get(
            "/api/incident-reports/?date_from=2025-04-01T00:00:00&date_to=2025-05-01T00:00:00", headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json() == []

    def test_filter_date_combined_with_status(self, session, auth_headers, sample_type, creator_user):
        dates = [datetime(2025, 1, 1), datetime(2025, 2, 1), datetime(2025, 3, 1)]
        statuses = [IncidentStatus.REPORTED, IncidentStatus.CONFIRMED, IncidentStatus.REPORTED]
        for d, s in zip(dates, statuses):
            report = IncidentReport(
                incident_type_id=sample_type.uid,
                severity=3,
                status=s,
                escalation_level=EscalationLevel.NONE,
                reported_by_user_id=creator_user.uid,
                occurred_at=d,
            )
            session.add(report)
        session.commit()

        response = client.get(
            "/api/incident-reports/?date_from=2025-01-15T00:00:00&status=reported", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        for r in data:
            assert r["status"] == "reported"
            assert r["occurred_at"] >= "2025-01-15T00:00:00"


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
        assert "subjects" in data

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

    def test_update_subjects_replaces_all(
        self, session, admin_auth_headers, sample_type, creator_user, authenticated_user
    ):
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

        # Add initial subject
        subject = IncidentReportSubject(
            incident_report_id=report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.WITNESS,
        )
        session.add(subject)
        session.commit()

        # Update with new subjects — should replace all
        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"subjects": [{"user_id": str(authenticated_user.uid), "role": "responsible"}]},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["subjects"]) == 1
        assert data["subjects"][0]["user_id"] == str(authenticated_user.uid)
        assert data["subjects"][0]["role"] == "responsible"

    def test_update_without_subjects_preserves_existing(self, session, admin_auth_headers, sample_type, creator_user):
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

        subject = IncidentReportSubject(
            incident_report_id=report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.WITNESS,
        )
        session.add(subject)
        session.commit()

        # Update status only — subjects untouched
        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"status": "confirmed"},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert len(data["subjects"]) == 1
        assert data["subjects"][0]["role"] == "witness"

    def test_update_subjects_clear_all(self, session, admin_auth_headers, sample_type, creator_user):
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

        subject = IncidentReportSubject(
            incident_report_id=report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.WITNESS,
        )
        session.add(subject)
        session.commit()

        # Pass empty subjects list — should clear all
        response = client.put(
            f"/api/incident-reports/{report.uid}",
            json={"subjects": []},
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["subjects"] == []

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

    def test_delete_report_cascades_subjects(self, session, admin_auth_headers, sample_type, creator_user):
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

        subject = IncidentReportSubject(
            incident_report_id=report.uid,
            user_id=creator_user.uid,
            role=SubjectRole.RESPONSIBLE,
        )
        session.add(subject)
        session.commit()
        session.refresh(subject)
        subject_uid = subject.uid

        response = client.delete(f"/api/incident-reports/{report.uid}", headers=admin_auth_headers)
        assert response.status_code == 200

        from sqlmodel import select

        result = session.exec(select(IncidentReportSubject).where(IncidentReportSubject.uid == subject_uid)).first()
        assert result is None

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
