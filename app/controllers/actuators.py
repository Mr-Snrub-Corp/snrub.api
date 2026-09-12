from datetime import UTC, datetime
from uuid import UUID

from app.core.config import settings
from app.models.actuators import Actuator, ActuatorKind, ActuatorSetRequest, ActuatorState
from app.services.mqtt import MqttPublisher
from app.services.plant_model import ACTUATOR_NOMINAL

ACTUATOR_KIND: dict[Actuator, ActuatorKind] = {
    Actuator.ROD_POSITION: ActuatorKind.COMMAND,
    Actuator.PUMP_SPEED: ActuatorKind.COMMAND,
    Actuator.STEAM_VALVE: ActuatorKind.COMMAND,
    Actuator.LEAK_RATE: ActuatorKind.FAULT,
    Actuator.XENON_INJECTION: ActuatorKind.FAULT,
}


#  The request body { "value": 20 } gets parsed into an instance of a model
# class before your set_actuator function runs
async def set_actuator(
    actuator: Actuator, data: ActuatorSetRequest, user_id: UUID, publisher: MqttPublisher
) -> ActuatorState:
    topic = f"{settings.MQTT_BASE_TOPIC}/plant/actuators/{actuator.value}"
    payload = {
        "actuator": actuator.value,
        "value": data.value,
        "kind": ACTUATOR_KIND[actuator].value,
        "set_by": str(user_id),
        "ts": datetime.now(UTC),
    }
    await publisher.publish(topic, payload, retain=True)
    return ActuatorState(actuator=actuator, value=data.value, kind=ACTUATOR_KIND[actuator])


def get_actuators() -> list[ActuatorState]:
    """Current actuator positions to hydrate the client on load.

    The API is stateless and there's no actuator persistence yet, so this
    returns each actuator's nominal position. The client tolerates this as a
    default (docs/phase4-client-handover.md). Swap to last-known state if/when
    setpoints are persisted (e.g. read from retained MQTT or a table).
    """
    return [
        ActuatorState(actuator=actuator, value=ACTUATOR_NOMINAL[actuator.value], kind=ACTUATOR_KIND[actuator])
        for actuator in Actuator
    ]
