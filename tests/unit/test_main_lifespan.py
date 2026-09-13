import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.main import MQTT_CONNECT_ATTEMPTS, lifespan


def test_lifespan_survives_broker_down():
    """A down broker must not stop the API booting (app/main.py lifespan)."""
    app = SimpleNamespace(state=SimpleNamespace())
    publisher = AsyncMock()
    publisher.connect.side_effect = ConnectionError("broker refused")

    async def scenario():
        with (
            patch("app.main.MqttPublisher", return_value=publisher),
            patch("app.main.asyncio.sleep", new_callable=AsyncMock),
        ):
            async with lifespan(app):
                assert app.state.mqtt_publisher is publisher
        assert publisher.connect.await_count == MQTT_CONNECT_ATTEMPTS
        publisher.disconnect.assert_awaited_once()

    asyncio.run(scenario())


def test_lifespan_retries_then_connects():
    app = SimpleNamespace(state=SimpleNamespace())
    publisher = AsyncMock()
    publisher.connect.side_effect = [ConnectionError("name resolution"), None]

    async def scenario():
        with (
            patch("app.main.MqttPublisher", return_value=publisher),
            patch("app.main.asyncio.sleep", new_callable=AsyncMock) as sleep,
        ):
            async with lifespan(app):
                assert app.state.mqtt_publisher is publisher
        assert publisher.connect.await_count == 2
        sleep.assert_awaited_once()

    asyncio.run(scenario())
