from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from app.controllers.godmode import GOD_MODE_MARKER, LEVER_CODE_MAP
from app.controllers.incident_report import get_reports_for_telemetry
from app.main import app
from app.models.godmode import GodModeLever
from app.models.incident_report import EscalationLevel, IncidentReport, IncidentStatus
from app.services.telemetry import TRACKED_INCIDENT_TYPE_CODES, compute_targets

client = TestClient(app)

ACTIVE_STATUSES = ["reported", "under_review", "confirmed", "mitigation_in_progress"]


def _genuine_report(session, incident_type_id, user):
    """A real operator-filed report (no God-mode marker) for the same incident type."""
    report = IncidentReport(
        incident_type_id=incident_type_id,
        severity=5,
        status=IncidentStatus.REPORTED,
        escalation_level=EscalationLevel.NONE,
        reported_by_user_id=user.uid,
        occurred_at=datetime.utcnow(),
        description=None,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


class TestGodModeAuth:
    """Only super_admin may reach the God-mode endpoints."""

    def test_get_levers_super_admin_ok(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.get("/api/godmode/levers", headers=super_admin_auth_headers)
        assert response.status_code == 200

    def test_put_lever_super_admin_ok(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.put(
            "/api/godmode/levers/control_rod",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("headers_fixture", ["admin_auth_headers", "creator_auth_headers", "auth_headers"])
    def test_get_levers_non_super_admin_forbidden(self, session, request, headers_fixture, godmode_incident_types):
        headers = request.getfixturevalue(headers_fixture)
        response = client.get("/api/godmode/levers", headers=headers)
        assert response.status_code == 403

    @pytest.mark.parametrize("headers_fixture", ["admin_auth_headers", "creator_auth_headers", "auth_headers"])
    def test_put_lever_non_super_admin_forbidden(self, session, request, headers_fixture, godmode_incident_types):
        headers = request.getfixturevalue(headers_fixture)
        response = client.put(
            "/api/godmode/levers/control_rod",
            json={"status": "confirmed"},
            headers=headers,
        )
        assert response.status_code == 403

    def test_get_levers_unauthenticated(self, session, godmode_incident_types):
        response = client.get("/api/godmode/levers")
        assert response.status_code in (401, 403)

    def test_put_lever_unauthenticated(self, session, godmode_incident_types):
        response = client.put("/api/godmode/levers/control_rod", json={"status": "confirmed"})
        assert response.status_code in (401, 403)


class TestSetLever:
    def test_create_activates_malfunction(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.put(
            "/api/godmode/levers/control_rod",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["lever"] == "control_rod"
        assert result["incident_type_code"] == "control_rod_anomaly"
        assert result["active"] is True
        assert result["status"] == "confirmed"
        assert result["intensity"] == 1.0
        assert result["report_uid"] is not None

    def test_upsert_does_not_stack_reports(self, session, super_admin_auth_headers, godmode_incident_types):
        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "reported"},
            headers=super_admin_auth_headers,
        )
        response = client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

        reports = get_reports_for_telemetry(session, ACTIVE_STATUSES, ["primary_coolant_loss"])
        assert len(reports) == 1
        assert reports[0].status == "confirmed"

    def test_off_deactivates_lever(self, session, super_admin_auth_headers, godmode_incident_types):
        client.put(
            "/api/godmode/levers/xenon",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        response = client.put(
            "/api/godmode/levers/xenon",
            json={"status": "resolved"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["active"] is False
        assert result["intensity"] == 0.0
        assert result["status"] is None
        assert result["report_uid"] is None

    def test_off_with_no_existing_report_is_noop(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.put(
            "/api/godmode/levers/steam_pressure",
            json={"status": "resolved"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200
        result = response.json()
        assert result["active"] is False
        assert result["report_uid"] is None

        # No God-mode report was created for this lever (scoped to the marker,
        # so this holds regardless of any seeded/genuine reports of the same type).
        marked = session.exec(
            select(IncidentReport)
            .where(IncidentReport.incident_type_id == godmode_incident_types["steam_pressure_anomaly"].uid)
            .where(IncidentReport.description.startswith(GOD_MODE_MARKER))  # pylint: disable=no-member
        ).all()
        assert marked == []

    def test_unknown_lever_rejected(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.put(
            "/api/godmode/levers/not_a_lever",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 422


class TestTelemetryEffect:
    """Levers steer the incident-derived targets; the simulator process
    (app/simulator.py) integrates telemetry toward them (Phase 3)."""

    def _targets(self, session):
        reports = get_reports_for_telemetry(session, ACTIVE_STATUSES, TRACKED_INCIDENT_TYPE_CODES)
        return compute_targets(reports)

    def test_confirmed_lever_shifts_targets(self, session, super_admin_auth_headers, godmode_incident_types):
        baseline = self._targets(session)

        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )

        # primary_coolant_loss: coolant_flow_rate -20, core_temperature +150 (weight 1.0)
        shifted = self._targets(session)
        assert shifted["coolant_flow_rate"] == baseline["coolant_flow_rate"] - 20
        assert shifted["core_temperature"] == baseline["core_temperature"] + 150

    def test_off_restores_baseline(self, session, super_admin_auth_headers, godmode_incident_types):
        baseline = self._targets(session)

        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "resolved"},
            headers=super_admin_auth_headers,
        )

        # Turning the lever off removes its report -> targets return to baseline
        # exactly (targets are deterministic; noise now lives in the sensors).
        restored = self._targets(session)
        assert restored == baseline


class TestGetLevers:
    def test_returns_all_five_levers(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.get("/api/godmode/levers", headers=super_admin_auth_headers)
        assert response.status_code == 200
        states = response.json()
        assert len(states) == len(GodModeLever)

    @pytest.mark.parametrize("lever,code", list(LEVER_CODE_MAP.items()))
    def test_lever_maps_to_expected_code(self, session, super_admin_auth_headers, godmode_incident_types, lever, code):
        response = client.get("/api/godmode/levers", headers=super_admin_auth_headers)
        states = {s["lever"]: s for s in response.json()}
        assert states[lever.value]["incident_type_code"] == code

    def test_reflects_active_lever(self, session, super_admin_auth_headers, godmode_incident_types):
        client.put(
            "/api/godmode/levers/xenon",
            json={"status": "under_review"},
            headers=super_admin_auth_headers,
        )
        response = client.get("/api/godmode/levers", headers=super_admin_auth_headers)
        states = {s["lever"]: s for s in response.json()}
        assert states["xenon"]["active"] is True
        assert states["xenon"]["status"] == "under_review"
        assert states["xenon"]["intensity"] == 0.6


class TestGodModeMarker:
    def test_created_report_carries_marker(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.put(
            "/api/godmode/levers/xenon",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        uid = UUID(response.json()["report_uid"])
        report = session.get(IncidentReport, uid)
        assert report.description.startswith(GOD_MODE_MARKER)

    def test_lever_ignores_genuine_report(
        self, session, super_admin_auth_headers, godmode_incident_types, creator_user
    ):
        pcl_type = godmode_incident_types["primary_coolant_loss"]
        genuine = _genuine_report(session, pcl_type.uid, creator_user)

        response = client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )

        # God mode creates its own report, never adopting the genuine one.
        assert response.json()["report_uid"] != str(genuine.uid)

        session.refresh(genuine)
        assert genuine.status == IncidentStatus.REPORTED
        assert genuine.description is None

        # Two distinct reports now exist for the type (genuine + God-mode).
        assert len(get_reports_for_telemetry(session, ACTIVE_STATUSES, ["primary_coolant_loss"])) == 2

    def test_off_leaves_genuine_report_untouched(
        self, session, super_admin_auth_headers, godmode_incident_types, creator_user
    ):
        pcl_type = godmode_incident_types["primary_coolant_loss"]
        genuine = _genuine_report(session, pcl_type.uid, creator_user)

        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "resolved"},
            headers=super_admin_auth_headers,
        )

        # Turning the lever off must not resolve the genuine incident.
        session.refresh(genuine)
        assert genuine.status == IncidentStatus.REPORTED
