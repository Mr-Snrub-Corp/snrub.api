from uuid import UUID

from sqlmodel import Session

from ..db.crud_base import CRUDBase
from ..models.incident_category import IncidentCategory, IncidentCategoryResponse

category_crud = CRUDBase(IncidentCategory)


def get_category(uid: UUID, session: Session):
    category = category_crud.get(session, uid)
    return IncidentCategoryResponse.model_validate(category)


def get_categories(session: Session):
    categories = category_crud.get_all(session)
    return [IncidentCategoryResponse.model_validate(c) for c in categories]
