from uuid import UUID

from fastapi import APIRouter, Depends

from app.controllers.actuators import get_actuators, set_actuator
from app.models.actuators import Actuator, ActuatorSetRequest
from app.services.mqtt import MqttPublisher, get_mqtt_publisher

from ..security.authorization import verify_super_admin_access

router = APIRouter(prefix="/godmode", tags=["God Mode"])


@router.get("/actuators")
async def list_actuators(
    user_data: dict = Depends(verify_super_admin_access),
):
    return get_actuators()


@router.put("/actuators/{actuator}")
async def set_actuator_endpoint(
    actuator: Actuator,
    data: ActuatorSetRequest,
    user_data: dict = Depends(verify_super_admin_access),
    publisher: MqttPublisher = Depends(get_mqtt_publisher),
):
    return await set_actuator(actuator, data, UUID(user_data["uid"]), publisher)
