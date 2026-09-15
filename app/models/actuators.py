from enum import StrEnum

from sqlmodel import Field, SQLModel


class Actuator(StrEnum):
    """God-mode actuators (Phase 4, docs/roadmap.md). Continuous levers the
    super_admin route publishes to snrub/plant/actuators/{actuator}; the plant
    model folds them into its targets. Command vs fault split is in ACTUATOR_KIND."""

    ROD_POSITION = "rod_position"
    PUMP_SPEED = "pump_speed"
    STEAM_VALVE = "steam_valve"
    LEAK_RATE = "leak_rate"
    XENON_INJECTION = "xenon_injection"


class ActuatorKind(StrEnum):
    """How an actuator drives the plant: a normal operating command
    (rod/pump/steam) or an injected malfunction (leak/xenon)."""

    COMMAND = "command"
    FAULT = "fault"


class ActuatorSetRequest(SQLModel):
    """Set one actuator. value is 0-100 for every actuator (percent open/inserted
    for commands, fault intensity for faults)."""

    value: float = Field(ge=0, le=100)


class ActuatorState(SQLModel):
    """Current position of a single actuator, echoed back after a set."""

    actuator: Actuator
    value: float
    kind: ActuatorKind
