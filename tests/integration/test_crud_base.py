"""Tests for the generic CRUDBase every controller inherits.

The error paths are driven by real failures -- a duplicate unique `code`, an FK
still referencing a row, a field name that does not exist on the model -- rather
than by mocking the session. If the try/except wrapping in CRUDBase stops
converting those into HTTPExceptions, these fail.

`incident_categories.code` is unique and `incident_types.category_id` is a
restricting FK, which is why IncidentCategory is the model used throughout.
"""

from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlmodel import SQLModel, select

from app.db.crud_base import CRUDBase
from app.models.incident_category import IncidentCategory

category_crud = CRUDBase(IncidentCategory)


def _category(code: str | None = None, name: str = "Test Category") -> IncidentCategory:
    """Build an unsaved category with a code that will not collide by accident."""
    return IncidentCategory(code=code or f"crud_{uuid4().hex[:8]}", name=name)


class _CodeUpdate(SQLModel):
    """Partial-update payload, so model_dump(exclude_unset=True) yields only `code`."""

    code: str


def _fetch(session, uid):
    return session.exec(select(IncidentCategory).where(IncidentCategory.uid == uid)).first()


class TestCreate:
    def test_create_persists_and_returns_populated_object(self, session):
        created = category_crud.create(session, _category(name="Fresh"))

        assert created.uid is not None
        assert created.created is not None
        assert _fetch(session, created.uid).name == "Fresh"

    def test_create_duplicate_code_returns_500_and_rolls_back(self, session, sample_category):
        with pytest.raises(HTTPException) as exc:
            category_crud.create(session, _category(code=sample_category.code, name="Duplicate"))

        assert exc.value.status_code == 500
        assert exc.value.detail == "Internal server error"

        # Rollback must leave exactly the pre-existing row behind.
        rows = session.exec(select(IncidentCategory).where(IncidentCategory.code == sample_category.code)).all()
        assert len(rows) == 1
        assert rows[0].uid == sample_category.uid
        assert rows[0].name == sample_category.name


class TestCreateMany:
    def test_create_many_persists_every_object(self, session):
        objs = [_category(name=f"Batch {i}") for i in range(3)]

        created = category_crud.create_many(session, objs)

        assert len(created) == 3
        for obj in created:
            assert obj.uid is not None
            assert _fetch(session, obj.uid) is not None

    def test_create_many_rolls_back_whole_batch_on_conflict(self, session):
        code = f"crud_{uuid4().hex[:8]}"
        objs = [_category(code=code, name="First"), _category(code=code, name="Second")]

        with pytest.raises(HTTPException) as exc:
            category_crud.create_many(session, objs)

        assert exc.value.status_code == 500
        # All-or-nothing: the valid first row must not survive either.
        assert session.exec(select(IncidentCategory).where(IncidentCategory.code == code)).all() == []


class TestGet:
    def test_get_unknown_uid_returns_404(self, session):
        with pytest.raises(HTTPException) as exc:
            category_crud.get(session, uuid4())

        assert exc.value.status_code == 404
        assert exc.value.detail == "Object not found"

    def test_get_with_unknown_primary_key_field_returns_500(self, session, sample_category):
        # getattr on a field the model does not have raises AttributeError, which
        # must surface as a 500 and not leak the AttributeError.
        broken = CRUDBase(IncidentCategory, primary_key_field="not_a_column")

        with pytest.raises(HTTPException) as exc:
            broken.get(session, sample_category.uid)

        assert exc.value.status_code == 500
        assert exc.value.detail == "Internal server error"


class TestGetByEmail:
    def test_get_by_email_on_model_without_email_returns_500(self, session):
        # IncidentCategory has no `email` column, so self.model.email raises.
        with pytest.raises(HTTPException) as exc:
            category_crud.get_by_email(session, "nobody@example.com")

        assert exc.value.status_code == 500
        assert exc.value.detail == "Internal server error"


class TestUpdate:
    def test_update_unknown_uid_returns_404(self, session):
        with pytest.raises(HTTPException) as exc:
            category_crud.update(session, uuid4(), _CodeUpdate(code="whatever"))

        assert exc.value.status_code == 404
        assert exc.value.detail == "Object not found"

    def test_update_to_duplicate_code_returns_500_and_leaves_row_unchanged(self, session, sample_category):
        target = category_crud.create(session, _category(name="Target"))
        original_code = target.code

        with pytest.raises(HTTPException) as exc:
            category_crud.update(session, target.uid, _CodeUpdate(code=sample_category.code))

        assert exc.value.status_code == 500
        assert _fetch(session, target.uid).code == original_code


class TestDelete:
    def test_delete_removes_row(self, session):
        created = category_crud.create(session, _category())

        category_crud.delete(session, created.uid)

        assert _fetch(session, created.uid) is None

    def test_delete_unknown_uid_returns_404(self, session):
        with pytest.raises(HTTPException) as exc:
            category_crud.delete(session, uuid4())

        assert exc.value.status_code == 404
        assert exc.value.detail == "Object not found"

    def test_delete_referenced_row_returns_500_and_keeps_row(self, session, sample_type):
        # sample_type holds an FK to its category, so the DELETE must be refused.
        category_uid = sample_type.category_id

        with pytest.raises(HTTPException) as exc:
            category_crud.delete(session, category_uid)

        assert exc.value.status_code == 500
        assert _fetch(session, category_uid) is not None


class TestFieldLookups:
    def test_get_multi_by_field_returns_matches(self, session):
        name = f"Shared {uuid4().hex[:6]}"
        category_crud.create_many(session, [_category(name=name), _category(name=name)])

        found = category_crud.get_multi_by_field(session, "name", name)

        assert len(found) == 2
        assert {obj.name for obj in found} == {name}

    def test_get_multi_by_field_unknown_field_returns_500(self, session):
        with pytest.raises(HTTPException) as exc:
            category_crud.get_multi_by_field(session, "not_a_column", "x")

        assert exc.value.status_code == 500

    def test_get_by_field_returns_none_when_absent(self, session):
        assert category_crud.get_by_field(session, "code", f"missing_{uuid4().hex}") is None

    def test_get_by_field_unknown_field_returns_500(self, session):
        with pytest.raises(HTTPException) as exc:
            category_crud.get_by_field(session, "not_a_column", "x")

        assert exc.value.status_code == 500


class TestGetAll:
    def test_get_all_includes_created_rows(self, session):
        created = category_crud.create(session, _category())

        uids = {obj.uid for obj in category_crud.get_all(session)}

        assert created.uid in uids


# ---------------------------------------------------------------------------
# Left for you to implement.
# ---------------------------------------------------------------------------


@pytest.mark.skip(reason="TODO: last uncovered branch in crud_base -- get_all's except (lines 59-61)")
def test_get_all_wraps_db_error_as_500(session):
    """get_all should convert a DB-layer failure into a 500, not propagate it.

    Every other except block here is reachable with a real constraint violation
    or a bad field name; get_all takes no arguments, so it needs the session
    itself to fail. Options: monkeypatch `session.exec` to raise, or close the
    underlying connection first. Pick whichever you'd rather see repeated for
    the other methods, since it sets the pattern.
    """
    raise NotImplementedError


@pytest.mark.skip(reason="TODO: assert exclude_unset semantics -- executed today but nothing checks it")
def test_update_only_writes_provided_fields(session, sample_category):
    """update() uses model_dump(exclude_unset=True), so omitted fields must survive.

    Line 95 runs in the happy-path tests, but no assertion proves the omitted
    fields keep their old values -- swapping it to model_dump() would still pass.
    Update only `name` via a partial payload and assert `code` and `description`
    are untouched.
    """
    raise NotImplementedError
