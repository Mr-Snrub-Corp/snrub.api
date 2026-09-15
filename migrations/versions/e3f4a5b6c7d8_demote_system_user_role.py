"""Demote system user from SUPER_ADMIN to CREATOR

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-09-13 00:00:00.000000

Idempotent for DBs that already ran d2e3f4a5b6c7 before it started demoting.
The emitter only needs reported_by_user_id — CREATOR is enough.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.core.config import settings

# revision identifiers, used by Alembic.
revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE users SET role = CAST(:role AS userrole) WHERE email IN (:current, :legacy)"),
        {"current": settings.SYSTEM_USER_EMAIL, "legacy": "system@snrub.local", "role": "CREATOR"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("UPDATE users SET role = CAST(:role AS userrole) WHERE email IN (:current, :legacy)"),
        {"current": settings.SYSTEM_USER_EMAIL, "legacy": "system@snrub.local", "role": "SUPER_ADMIN"},
    )
