"""Phase 4 super_admin actuator route (docs/roadmap.md:254-302).

TDD target for the paired route: PUT /api/godmode/actuators/{actuator}
validates a lever change and publishes it (retained) to
snrub/plant/actuators/{actuator}. JWT (verify_super_admin_access) is the gate;
the EMQX ACL is broker-side defence-in-depth (tested separately / manually).

The API's MQTT publisher (app/main.lifespan) is replaced here by a recording
fake via the get_mqtt_publisher dependency override — same idiom the session
fixture uses for get_session. The controller passes a dict payload to
publish(), so the fake records dicts directly (no JSON round-trip).
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.services.mqtt import get_mqtt_publisher

client = TestClient(app)


def _topic(actuator: str) -> str:
    return f"{settings.MQTT_BASE_TOPIC}/plant/actuators/{actuator}"


class FakePublisher:
    """Stand-in for the app-scoped MqttPublisher; records publish() calls."""

    def __init__(self) -> None:
        self.published: list[dict] = []
        self.connected = True

    async def publish(self, topic, payload, *, retain: bool = False, qos: int = 0) -> None:
        self.published.append({"topic": topic, "payload": payload, "retain": retain, "qos": qos})


@pytest.fixture
def fake_publisher():
    """Override the actuator route's publisher with a recorder."""
    fake = FakePublisher()
    app.dependency_overrides[get_mqtt_publisher] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_mqtt_publisher, None)


class TestActuatorAuth:
    """Only super_admin may drive actuators."""

    def test_put_actuator_super_admin_ok(self, session, super_admin_auth_headers, fake_publisher):
        response = client.put(
            "/api/godmode/actuators/pump_speed",
            json={"value": 20},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.parametrize("headers_fixture", ["admin_auth_headers", "creator_auth_headers", "auth_headers"])
    def test_put_actuator_non_super_admin_forbidden(self, session, request, headers_fixture, fake_publisher):
        headers = request.getfixturevalue(headers_fixture)
        response = client.put(
            "/api/godmode/actuators/pump_speed",
            json={"value": 20},
            headers=headers,
        )
        assert response.status_code == 403

    def test_put_actuator_unauthenticated(self, session, fake_publisher):
        response = client.put("/api/godmode/actuators/pump_speed", json={"value": 20})
        assert response.status_code in (401, 403)

    def test_forbidden_request_does_not_publish(self, session, auth_headers, fake_publisher):
        client.put("/api/godmode/actuators/pump_speed", json={"value": 20}, headers=auth_headers)
        assert fake_publisher.published == []


class TestActuatorValidation:
    def test_unknown_actuator_rejected(self, session, super_admin_auth_headers, fake_publisher):
        response = client.put(
            "/api/godmode/actuators/not_an_actuator",
            json={"value": 20},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 422

    @pytest.mark.parametrize("bad_value", [150, -5, 100.1])
    def test_out_of_range_value_rejected(self, session, super_admin_auth_headers, fake_publisher, bad_value):
        response = client.put(
            "/api/godmode/actuators/pump_speed",
            json={"value": bad_value},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 422

    def test_missing_value_rejected(self, session, super_admin_auth_headers, fake_publisher):
        response = client.put(
            "/api/godmode/actuators/pump_speed",
            json={},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 422

    def test_invalid_request_does_not_publish(self, session, super_admin_auth_headers, fake_publisher):
        client.put(
            "/api/godmode/actuators/pump_speed",
            json={"value": 150},
            headers=super_admin_auth_headers,
        )
        assert fake_publisher.published == []


class TestActuatorPublish:
    """The route republishes the lever change to the actuator topic (retained)."""

    def test_command_actuator_publishes_expected_message(
        self, session, super_admin_user, super_admin_auth_token, fake_publisher
    ):
        headers = {"Authorization": f"Bearer {super_admin_auth_token}"}
        response = client.put(
            "/api/godmode/actuators/pump_speed",
            json={"value": 20},
            headers=headers,
        )
        assert response.status_code == 200

        assert len(fake_publisher.published) == 1
        msg = fake_publisher.published[0]
        assert msg["topic"] == _topic("pump_speed")
        assert msg["retain"] is True  # retained so the simulator gets the last setpoint on resubscribe

        payload = msg["payload"]
        assert payload["actuator"] == "pump_speed"
        assert payload["value"] == 20
        assert payload["kind"] == "command"
        assert payload["set_by"] == str(super_admin_user.uid)
        assert "ts" in payload

    def test_fault_actuator_carries_fault_kind(self, session, super_admin_auth_headers, fake_publisher):
        response = client.put(
            "/api/godmode/actuators/xenon_injection",
            json={"value": 80},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200

        msg = fake_publisher.published[0]
        assert msg["topic"] == _topic("xenon_injection")  # topic must follow the actuator, not be hardcoded
        payload = msg["payload"]
        assert payload["actuator"] == "xenon_injection"
        assert payload["kind"] == "fault"

    def test_steam_valve_publishes_to_its_own_topic(self, session, super_admin_auth_headers, fake_publisher):
        # Regression: the enum member/value must be steam_valve (not steam_value), or the
        # topic and plant_model.ACTUATOR_NOMINAL lookup silently disagree.
        response = client.put(
            "/api/godmode/actuators/steam_valve",
            json={"value": 30},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200

        msg = fake_publisher.published[0]
        assert msg["topic"] == _topic("steam_valve")
        payload = msg["payload"]
        assert payload["actuator"] == "steam_valve"
        assert payload["kind"] == "command"

    def test_response_echoes_actuator_state(self, session, super_admin_auth_headers, fake_publisher):
        response = client.put(
            "/api/godmode/actuators/rod_position",
            json={"value": 75},
            headers=super_admin_auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["actuator"] == "rod_position"
        assert body["value"] == 75
        assert body["kind"] == "command"


class TestActuatorList:
    """GET /godmode/actuators hydrates the client with nominal positions + kinds."""

    def test_list_actuators_super_admin_returns_all_five(self, session, super_admin_auth_headers):
        response = client.get("/api/godmode/actuators", headers=super_admin_auth_headers)
        assert response.status_code == 200

        body = response.json()
        by_name = {a["actuator"]: a for a in body}
        assert set(by_name) == {"rod_position", "pump_speed", "steam_valve", "leak_rate", "xenon_injection"}
        # Commands default to their operating point; faults default to 0 (off).
        assert by_name["pump_speed"] == {"actuator": "pump_speed", "value": 80, "kind": "command"}
        assert by_name["steam_valve"]["value"] == 50
        assert by_name["leak_rate"] == {"actuator": "leak_rate", "value": 0, "kind": "fault"}

    @pytest.mark.parametrize("headers_fixture", ["admin_auth_headers", "creator_auth_headers", "auth_headers"])
    def test_list_actuators_non_super_admin_forbidden(self, session, request, headers_fixture):
        headers = request.getfixturevalue(headers_fixture)
        response = client.get("/api/godmode/actuators", headers=headers)
        assert response.status_code == 403

    def test_list_actuators_unauthenticated(self, session):
        response = client.get("/api/godmode/actuators")
        assert response.status_code in (401, 403)
