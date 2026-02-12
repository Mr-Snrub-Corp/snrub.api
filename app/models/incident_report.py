from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import Field, SQLModel


class IncidentStatus(StrEnum):
    REPORTED = "reported"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    FALSE_ALARM = "false_alarm"
    CONTAINED = "contained"
    MITIGATION_IN_PROGRESS = "mitigation_in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EscalationLevel(StrEnum):
    NONE = "none"
    MONITORING = "monitoring"
    ESCALATED = "escalated"
    EMERGENCY_STATE_DECLARED = "emergency_state_declared"


class IncidentReportBase(SQLModel, table=False):
    incident_type_id: UUID = Field(foreign_key="incident_types.uid")
    description: str | None = None
    severity: int = Field(ge=1, le=7)
    status: IncidentStatus = Field(default=IncidentStatus.REPORTED)
    escalation_level: EscalationLevel = Field(default=EscalationLevel.NONE)
    reported_by_user_id: UUID = Field(foreign_key="users.uid")
    occurred_at: datetime


class IncidentReport(IncidentReportBase, table=True):
    __tablename__ = "incident_reports"

    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class IncidentReportCreateRequest(SQLModel):
    incident_type_id: UUID
    description: str | None = None
    severity: int
    occurred_at: datetime

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: int) -> int:
        if not 1 <= v <= 7:
            raise ValueError("Severity must be 1-7 (INES scale)")
        return v


class IncidentReportUpdateRequest(SQLModel):
    description: str | None = None
    severity: int | None = None
    status: IncidentStatus | None = None
    escalation_level: EscalationLevel | None = None
    incident_type_id: UUID | None = None

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 7:
            raise ValueError("Severity must be 1-7 (INES scale)")
        return v


class IncidentReportResponse(IncidentReportBase):
    uid: UUID
    created: datetime
    updated: datetime
