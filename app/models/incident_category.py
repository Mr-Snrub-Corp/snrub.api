from datetime import datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class IncidentCategoryBase(SQLModel, table=False):
    code: str = Field(unique=True, index=True)
    name: str
    description: str | None = None


class IncidentCategory(IncidentCategoryBase, table=True):
    __tablename__ = "incident_categories"

    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)
    updated: datetime = Field(default_factory=datetime.utcnow)


class IncidentCategoryResponse(IncidentCategoryBase):
    uid: UUID
    created: datetime
    updated: datetime
