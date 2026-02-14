from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class SubjectRole(StrEnum):
    RESPONSIBLE = "responsible"
    INVOLVED = "involved"
    WITNESS = "witness"


class IncidentReportSubjectBase(SQLModel, table=False):
    incident_report_id: UUID = Field(foreign_key="incident_reports.uid", ondelete="CASCADE")
    user_id: UUID = Field(foreign_key="users.uid")
    role: SubjectRole


class IncidentReportSubject(IncidentReportSubjectBase, table=True):
    __tablename__ = "incident_report_subjects"

    uid: UUID = Field(default_factory=uuid4, primary_key=True)
    created: datetime = Field(default_factory=datetime.utcnow)


class IncidentReportSubjectCreateRequest(SQLModel):
    user_id: UUID
    role: SubjectRole


class IncidentReportSubjectResponse(IncidentReportSubjectBase):
    uid: UUID
    created: datetime
