from datetime import datetime
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlmodel import Field, SQLModel

from .validators import validate_ines_severity, validate_ines_severity_optional


class IncidentTypeBase(SQLModel, table=False):
    code: str = Field(unique=True, index=True)
    name: str
    category_id: UUID = Field(foreign_key="incident_categories.uid")
    default_severity: int = Field(ge=1, le=7)
    description: str | None = None


class IncidentType(IncidentTypeBase, table=True):
    __tablename__ = "incident_types"

    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class IncidentTypeCreateRequest(SQLModel):
    code: str
    name: str
    category_id: UUID
    default_severity: int
    description: str | None = None

    _validate_severity = field_validator("default_severity")(validate_ines_severity)


class IncidentTypeUpdateRequest(SQLModel):
    code: str | None = None
    name: str | None = None
    category_id: UUID | None = None
    default_severity: int | None = None
    description: str | None = None

    _validate_severity = field_validator("default_severity")(validate_ines_severity_optional)


class IncidentTypeResponse(IncidentTypeBase):
    uid: UUID
    created: datetime
    updated: datetime
