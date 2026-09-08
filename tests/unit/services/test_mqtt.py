import asyncio
import json
from unittest.mock import patch

import pytest

from app.core.config import settings
from app.services.mqtt import MqttPublisher


class FakeMqttClient:
    """Stand-in for aiomqtt.Client. Records connect/publish/disconnect."""

    def __init__(self, hostname, port, username, password):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.entered = False
        self.exited = False
        self.published: list[dict] = []

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.exited = True
        return False

    async def publish(self, topic, payload, qos=0, retain=False):
        self.published.append({"topic": topic, "payload": payload, "qos": qos, "retain": retain})


def _run(coro):
    return asyncio.run(coro)


class TestMqttPublisherInit:
    def test_defaults_come_from_settings(self):
        publisher = MqttPublisher()

        assert publisher._host == settings.MQTT_HOST
        assert publisher._port == settings.MQTT_PORT
        assert publisher._username == settings.MQTT_USERNAME
        assert publisher._password == settings.MQTT_PASSWORD
        assert publisher._client is None

    def test_explicit_args_override_settings(self):
        publisher = MqttPublisher(host="broker.local", port=2883, username="plant", password="secret")

        assert publisher._host == "broker.local"
        assert publisher._port == 2883
        assert publisher._username == "plant"
        assert publisher._password == "secret"

    def test_empty_username_is_kept_not_replaced_by_settings(self):
        publisher = MqttPublisher(username="", password="")

        assert publisher._username == ""
        assert publisher._password == ""


class TestMqttPublisherConnectDisconnect:
    def test_connect_enters_client_context(self):
        created: list[FakeMqttClient] = []

        def factory(**kwargs):
            client = FakeMqttClient(**kwargs)
            created.append(client)
            return client

        publisher = MqttPublisher(host="emqx", port=1883, username="u", password="p")

        with patch("app.services.mqtt.aiomqtt.Client", side_effect=factory):
            _run(publisher.connect())

        assert len(created) == 1
        client = created[0]
        assert client.hostname == "emqx"
        assert client.port == 1883
        assert client.username == "u"
        assert client.password == "p"
        assert client.entered is True
        assert publisher._client is client

    def test_disconnect_exits_client_and_clears_it(self):
        created: list[FakeMqttClient] = []

        def factory(**kwargs):
            client = FakeMqttClient(**kwargs)
            created.append(client)
            return client

        publisher = MqttPublisher(host="emqx", port=1883)

        async def scenario():
            with patch("app.services.mqtt.aiomqtt.Client", side_effect=factory):
                await publisher.connect()
                await publisher.disconnect()

        _run(scenario())

        assert created[0].exited is True
        assert publisher._client is None

    def test_disconnect_is_noop_when_never_connected(self):
        publisher = MqttPublisher()

        _run(publisher.disconnect())

        assert publisher._client is None


class TestMqttPublisherPublish:
    def test_publish_before_connect_raises(self):
        publisher = MqttPublisher()

        with pytest.raises(RuntimeError, match="before connect"):
            _run(publisher.publish("snrub/reactor/metrics", {"reactor_power": 95.0}))

    def test_publish_json_encodes_payload(self):
        created: list[FakeMqttClient] = []

        def factory(**kwargs):
            client = FakeMqttClient(**kwargs)
            created.append(client)
            return client

        publisher = MqttPublisher(host="emqx", port=1883)
        payload = {"reactor_power": 95.0, "level": "normal"}

        async def scenario():
            with patch("app.services.mqtt.aiomqtt.Client", side_effect=factory):
                await publisher.connect()
                await publisher.publish("snrub/reactor/metrics", payload)

        _run(scenario())

        assert created[0].published == [
            {
                "topic": "snrub/reactor/metrics",
                "payload": json.dumps(payload, default=str),
                "qos": 0,
                "retain": False,
            }
        ]

    def test_publish_passes_retain_and_qos(self):
        created: list[FakeMqttClient] = []

        def factory(**kwargs):
            client = FakeMqttClient(**kwargs)
            created.append(client)
            return client

        publisher = MqttPublisher(host="emqx", port=1883)
        payload = {"metric": "core_temperature", "level": "danger"}

        async def scenario():
            with patch("app.services.mqtt.aiomqtt.Client", side_effect=factory):
                await publisher.connect()
                await publisher.publish("snrub/alarms/core_temperature", payload, retain=True, qos=1)

        _run(scenario())

        published = created[0].published[0]
        assert published["retain"] is True
        assert published["qos"] == 1


@pytest.mark.skip(reason="TODO: implement later")
def test_reconnect_then_publish():
    """Connect, disconnect, connect again, then publish on the new client."""


@pytest.mark.skip(reason="TODO: implement later")
def test_publish_encodes_non_json_values_with_default_str():
    """Payload values that json.dumps cannot encode natively (e.g. datetime) go through default=str."""
