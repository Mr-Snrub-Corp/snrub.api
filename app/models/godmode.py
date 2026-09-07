from enum import StrEnum
from uuid import UUID

from sqlmodel import SQLModel

from .incident_report import IncidentStatus


class GodModeLever(StrEnum):
    """God-mode levers. Each maps to an existing incident_type_code (see LEVER_CODE_MAP)."""

    COOLANT_FLOW = "coolant_flow"
    CONTROL_ROD = "control_rod"
    PRIMARY_COOLANT_LOSS = "primary_coolant_loss"
    STEAM_PRESSURE = "steam_pressure"
    XENON = "xenon"


class LeverSetRequest(SQLModel):
    """Set a lever position. status is the ladder position; resolved/closed = off."""

    status: IncidentStatus
    severity: int | None = None  # defaults to the incident type's default_severity


class LeverState(SQLModel):
    """Current state of a single lever, derived from its backing incident report."""

    lever: GodModeLever
    incident_type_code: str
    active: bool  # False when no report or status weight == 0
    status: IncidentStatus | None
    intensity: float  # STATUS_WEIGHT[status], 0.0 when inactive
    report_uid: UUID | None
