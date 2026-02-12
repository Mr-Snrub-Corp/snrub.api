from uuid import UUID

from sqlmodel import Session

from ..db.crud_base import CRUDBase
from ..models.incident_type import (
    IncidentType,
    IncidentTypeCreateRequest,
    IncidentTypeResponse,
    IncidentTypeUpdateRequest,
)

type_crud = CRUDBase(IncidentType)


def create_type(data: IncidentTypeCreateRequest, session: Session):
    incident_type = type_crud.create(session, IncidentType(**data.model_dump()))
    return IncidentTypeResponse.model_validate(incident_type)


def get_type(uid: UUID, session: Session):
    incident_type = type_crud.get(session, uid)
    return IncidentTypeResponse.model_validate(incident_type)


def get_types(session: Session):
    types = type_crud.get_all(session)
    return [IncidentTypeResponse.model_validate(t) for t in types]


def get_types_by_category(category_id: UUID, session: Session):
    types = type_crud.get_multi_by_field(session, "category_id", category_id)
    return [IncidentTypeResponse.model_validate(t) for t in types]


def update_type(uid: UUID, data: IncidentTypeUpdateRequest, session: Session):
    incident_type = type_crud.update(session, uid, data)
    return IncidentTypeResponse.model_validate(incident_type)
