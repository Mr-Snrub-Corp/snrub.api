"""Add cascade delete to password_resets FK

Revision ID: a1b2c3d4e5f6
Revises: 5651397b89d0
Create Date: 2026-02-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '5651397b89d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('password_resets_user_id_fkey', 'password_resets', type_='foreignkey')
    op.create_foreign_key(
        'password_resets_user_id_fkey',
        'password_resets',
        'users',
        ['user_id'],
        ['uid'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('password_resets_user_id_fkey', 'password_resets', type_='foreignkey')
    op.create_foreign_key(
        'password_resets_user_id_fkey',
        'password_resets',
        'users',
        ['user_id'],
        ['uid'],
    )
