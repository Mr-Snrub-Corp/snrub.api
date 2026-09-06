import pytest
from fastapi.testclient import TestClient

from app.controllers.godmode import LEVER_CODE_MAP
from app.controllers.incident_report import get_reports_for_telemetry
from app.controllers.telemetry import get_reactor_metrics
from app.main import app
from app.models.godmode import GodModeLever

client = TestClient(app)

ACTIVE_STATUSES = ["reported", "under_review", "confirmed", "mitigation_in_progress"]


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
        assert response.json()["active"] is False
        reports = get_reports_for_telemetry(session, ACTIVE_STATUSES, ["steam_pressure_anomaly"])
        assert reports == []

    def test_unknown_lever_rejected(self, session, super_admin_auth_headers, godmode_incident_types):
        response = client.put(
            "/api/godmode/levers/not_a_lever",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 422


class TestTelemetryEffect:
    def test_confirmed_lever_shifts_metrics(self, session, super_admin_auth_headers, godmode_incident_types):
        baseline = get_reactor_metrics(session)

        client.put(
            "/api/godmode/levers/primary_coolant_loss",
            json={"status": "confirmed"},
            headers=super_admin_auth_headers,
        )

        # primary_coolant_loss: coolant_flow_rate -20, core_temperature +150 (weight 1.0)
        shifted = get_reactor_metrics(session)
        assert shifted["coolant_flow_rate"] < baseline["coolant_flow_rate"] - 10
        assert shifted["core_temperature"] > baseline["core_temperature"] + 100

    def test_off_restores_baseline(self, session, super_admin_auth_headers, godmode_incident_types):
        baseline = get_reactor_metrics(session)

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

        # Turning the lever off removes its report -> metrics return to baseline (modulo noise).
        restored = get_reactor_metrics(session)
        assert abs(restored["coolant_flow_rate"] - baseline["coolant_flow_rate"]) < 2
        assert abs(restored["core_temperature"] - baseline["core_temperature"]) < 10


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
