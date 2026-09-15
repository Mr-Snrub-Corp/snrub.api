"""Rename system user email off the reserved .local TLD

Revision ID: d2e3f4a5b6c7
Revises: c1a2b3d4e5f6
Create Date: 2026-09-13 00:00:00.000000

c1a2b3d4e5f6 seeded system@snrub.local. EmailStr (used by UserResponse) rejects
.local as a special-use TLD, so GET /api/users 500s once that row exists.
Also demotes the system user to CREATOR if an earlier revision seeded SUPER_ADMIN.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, None] = "c1a2b3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD = "system@snrub.local"
_NEW = "system@snrub.io"


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE users SET email = :new WHERE email = :old"), {"old": _OLD, "new": _NEW})
    bind.execute(
        sa.text("UPDATE users SET role = CAST(:role AS userrole) WHERE email IN (:old, :new)"),
        {"old": _OLD, "new": _NEW, "role": "CREATOR"},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE users SET email = :old WHERE email = :new"), {"old": _OLD, "new": _NEW})
