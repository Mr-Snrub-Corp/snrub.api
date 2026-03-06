import logging
from typing import Any, Generic, TypeVar
from uuid import UUID

from fastapi import HTTPException
from sqlmodel import Session, SQLModel, select

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType", bound=SQLModel)


class CRUDBase(Generic[ModelType]):
    """Base class for CRUD operations on SQLModel models.

    Provides basic Create, Read, Update, Delete operations for database models.

    Args:
        ModelType: The SQLModel class that this CRUD handler will operate on
        primary_key_field: The name of the primary key field (default: "uid")
    """

    def __init__(self, model: type[ModelType], primary_key_field: str = "uid"):
        self.model = model
        self.primary_key_field = primary_key_field

    def create(self, session: Session, obj_in: SQLModel) -> ModelType:
        """Add single object to database"""
        try:
            db_obj = self.model(**obj_in.model_dump())
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj
        except Exception as e:
            session.rollback()
            logger.exception("Failed to create %s", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get(self, session: Session, uid: UUID) -> ModelType:
        """Get single object from database by primary key"""
        try:
            pk_column = getattr(self.model, self.primary_key_field)
            db_obj = session.exec(select(self.model).where(pk_column == uid)).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail="Object not found")
            return db_obj
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Failed to get %s", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_all(self, session: Session) -> list[ModelType]:
        """Get all objects from database table"""
        try:
            db_objs = session.exec(select(self.model)).all()
            return list(db_objs)
        except Exception as e:
            logger.exception("Failed to get all %s", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_by_email(self, session: Session, email: str) -> ModelType | None:
        """Get single object from database by email"""
        try:
            return session.exec(select(self.model).where(self.model.email == email)).first()
        except Exception as e:
            logger.exception("Failed to get %s by email", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def create_many(self, session: Session, objects: list[SQLModel]) -> list[ModelType]:
        """Add multiple objects to database"""
        try:
            db_objects = [self.model(**obj.model_dump()) for obj in objects]
            session.add_all(db_objects)
            session.commit()
            for obj in db_objects:
                session.refresh(obj)
            return db_objects
        except Exception as e:
            session.rollback()
            logger.exception("Failed to create multiple %s", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def update(self, session: Session, uid: UUID, obj_in: SQLModel) -> ModelType:
        """Update an object in database by primary key."""
        try:
            # First fetch the existing object using the dynamic primary key field
            pk_column = getattr(self.model, self.primary_key_field)
            db_obj = session.exec(select(self.model).where(pk_column == uid)).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail="Object not found")

            # Update only the fields that are present in obj_in
            obj_data = obj_in.model_dump(exclude_unset=True)
            for key, value in obj_data.items():
                setattr(db_obj, key, value)

            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.exception("Failed to update %s", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def delete(self, session: Session, uid: UUID) -> None:
        """Delete an object from database by primary key."""
        try:
            pk_column = getattr(self.model, self.primary_key_field)
            db_obj = session.exec(select(self.model).where(pk_column == uid)).first()
            if not db_obj:
                raise HTTPException(status_code=404, detail="Object not found")
            session.delete(db_obj)
            session.commit()
        except HTTPException:
            raise
        except Exception as e:
            session.rollback()
            logger.exception("Failed to delete %s", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_multi_by_field(
        self,
        session: Session,
        field_name: str,
        value: Any,  # noqa: ANN401
    ) -> list[ModelType]:
        """Get multiple objects from database by field value"""
        try:
            field = getattr(self.model, field_name)
            db_objs = session.exec(select(self.model).where(field == value)).all()
            return list(db_objs)
        except Exception as e:
            logger.exception("Failed to get multiple %s by field", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e

    def get_by_field(
        self,
        session: Session,
        field: str,
        value: Any,  # noqa: ANN401
    ) -> ModelType | None:
        """Get single object from database by any column value"""
        try:
            column = getattr(self.model, field)
            return session.exec(select(self.model).where(column == value)).first()
        except Exception as e:
            logger.exception("Failed to get %s by field", self.model.__name__)
            raise HTTPException(status_code=500, detail="Internal server error") from e
