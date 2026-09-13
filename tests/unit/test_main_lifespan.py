import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.main import lifespan


def test_lifespan_survives_broker_down():
    """A down broker must not stop the API booting (app/main.py lifespan)."""
    app = SimpleNamespace(state=SimpleNamespace())
    publisher = AsyncMock()
    publisher.connect.side_effect = ConnectionError("broker refused")

    async def scenario():
        with patch("app.main.MqttPublisher", return_value=publisher):
            async with lifespan(app):
                assert app.state.mqtt_publisher is publisher
        publisher.disconnect.assert_awaited_once()

    asyncio.run(scenario())
