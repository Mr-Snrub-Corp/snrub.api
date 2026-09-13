"""Reusable async MQTT client (thin wrapper over aiomqtt).

Holds a single long-lived connection for a caller (the telemetry publisher
loop now; the simulator process in Phase 3; the API's actuator route in
Phase 4). JSON-encodes dict payloads. The single client both publishes and
subscribes (the simulator subscribes to the actuator tree while it publishes
telemetry).
"""

import json
from collections.abc import AsyncGenerator
from logging import getLogger

import aiomqtt
from fastapi import HTTPException, Request

from app.core.config import settings

logger = getLogger(__name__)


class MqttPublisher:
    """Owns one aiomqtt connection. Call connect() before publish()/subscribe()."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self._host = host or settings.MQTT_HOST
        self._port = port or settings.MQTT_PORT
        self._username = username if username is not None else settings.MQTT_USERNAME
        self._password = password if password is not None else settings.MQTT_PASSWORD
        self._client: aiomqtt.Client | None = None

    @property
    def connected(self) -> bool:
        return self._client is not None

    async def connect(self) -> None:
        client = aiomqtt.Client(
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
        )
        # aiomqtt has no standalone connect(); drive the context manager manually
        # so this object can be reused across a long-running loop.
        await client.__aenter__()
        self._client = client
        logger.info("MQTT connected to %s:%s", self._host, self._port)

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None
            logger.info("MQTT disconnected")

    async def publish(
        self,
        topic: str,
        payload: dict[str, object],
        *,
        retain: bool = False,
        qos: int = 0,
    ) -> None:
        if self._client is None:
            raise RuntimeError("MqttPublisher.publish called before connect()")
        await self._client.publish(topic, payload=json.dumps(payload, default=str), qos=qos, retain=retain)

    async def subscribe(self, topic: str, *, qos: int = 0) -> None:
        if self._client is None:
            raise RuntimeError("MqttPublisher.subscribe called before connect()")
        await self._client.subscribe(topic, qos=qos)

    @property
    def messages(self) -> AsyncGenerator[aiomqtt.Message]:
        """Async iterator of incoming messages on subscribed topics."""
        if self._client is None:
            raise RuntimeError("MqttPublisher.messages accessed before connect()")
        return self._client.messages


def get_mqtt_publisher(request: Request) -> MqttPublisher:
    """FastAPI dependency: the app-scoped publisher connected in main.lifespan.

    503 if the broker was unreachable at startup / dropped — the caller
    (super_admin actuator route) can't publish without a live connection.
    """
    publisher: MqttPublisher | None = getattr(request.app.state, "mqtt_publisher", None)
    if publisher is None or not publisher.connected:
        raise HTTPException(status_code=503, detail="MQTT broker unavailable")
    return publisher
