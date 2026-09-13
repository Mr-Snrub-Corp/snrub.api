"""Seed system user for auto-emitted incident reports (Phase 4)

Revision ID: c1a2b3d4e5f6
Revises: b0aa6c40fefe
Create Date: 2026-09-12 00:00:00.000000

The Phase 4 incident_emitter files auto-incidents under this identity, looked
up by settings.SYSTEM_USER_EMAIL (no hardcoded uid). Idempotent: skips if the
email already exists. Role is CREATOR — enough to own reported_by_user_id,
not god-mode. The password is a bcrypt hash of a random secret, so the
account can never be logged into (nobody knows the plaintext) while password
verification still runs without error.
"""

import secrets
import uuid
from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = 'c1a2b3d4e5f6'
down_revision: Union[str, None] = 'b0aa6c40fefe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Mirror app.controllers.user.pwd_context so a login attempt verifies cleanly (and fails).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__ident="2b")


def upgrade() -> None:
    bind = op.get_bind()
    email = settings.SYSTEM_USER_EMAIL

    already_seeded = bind.execute(
        sa.text("SELECT 1 FROM users WHERE email IN (:current, :legacy)"),
        {"current": email, "legacy": "system@snrub.local"},
    ).first()
    if already_seeded:
        return

    now = datetime.utcnow()
    bind.execute(
        sa.text(
            "INSERT INTO users (uid, email, name, role, status, password, created, updated) VALUES "
            "(CAST(:uid AS uuid), :email, :name, CAST(:role AS userrole), CAST(:status AS userstatus), "
            ":password, :created, :updated)"
        ),
        {
            "uid": str(uuid.uuid4()),
            "email": email,
            "name": "System",
            "role": "CREATOR",
            "status": "ACTIVE",
            "password": pwd_context.hash(secrets.token_urlsafe(32)),
            "created": now,
            "updated": now,
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM users WHERE email IN (:current, :legacy)"),
        {"current": settings.SYSTEM_USER_EMAIL, "legacy": "system@snrub.local"},
    )
