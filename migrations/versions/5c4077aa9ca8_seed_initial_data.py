"""Seed initial data (no-op: seeding moved to seeds/seed_runner.py)

Revision ID: 5c4077aa9ca8
Revises: 3a0ad4758705
Create Date: 2025-05-23 08:00:11.235202

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '5c4077aa9ca8'
down_revision: Union[str, None] = '3a0ad4758705'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
