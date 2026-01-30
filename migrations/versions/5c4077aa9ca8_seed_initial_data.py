"""Seed initial data

Revision ID: 5c4077aa9ca8
Revises: 3a0ad4758705
Create Date: 2025-05-23 08:00:11.235202

"""
from typing import Sequence, Union
from datetime import datetime
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.sql import table, column
from app.models.user import UserRole

# revision identifiers, used by Alembic.
revision: str = '5c4077aa9ca8'
down_revision: Union[str, None] = '3a0ad4758705'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define table structure for bulk insert
    users = table('users',
        column('uid', sa.Uuid),
        column('email', sa.String),
        column('name', sa.String),
        column('role', sa.Enum(UserRole)),
        column('password', sa.String),
        column('created', sa.DateTime),
        column('updated', sa.DateTime),
    )

    # Insert seed data
    op.bulk_insert(users, [
        {
            'uid': uuid4(),
            'email': 'motbollox@gmail.com',
            'name': 'The real boss',
            'role': UserRole.SUPER_ADMIN,
            'password': '$2b$12$LKoKkbQe/6m7AU4RpaJay.47EVOsqJnaYn2Uqw4fi.FSdls/5zB1u',  # "password"
            'created': datetime.utcnow(),
            'updated': datetime.utcnow()
        },
        {
            'uid': uuid4(),
            'email': '80hurtz@gmail.com',
            'name': 'Another influencer',
            'role': UserRole.CREATOR,
            'password': '$2b$12$8SDN58WEeDmeDQLYZEdwPO0ImS2.6ejbntDhKmzBi9kTaWvMtJfy2',  # "password"
            'created': datetime.utcnow(),
            'updated': datetime.utcnow()
        },
        {
            'uid': uuid4(),
            'email': 'follower@example.com',
            'name': 'Sheep da follower',
            'role': UserRole.VIEWER,
            'password': '$2b$12$0RNiB.7IWyYsKtl/Mwgt8OrqOXk.Mz5qwBFvI16sZ6RnGlAKh9ilq',  # "password"
            'created': datetime.utcnow(),
            'updated': datetime.utcnow()
        }
    ])


def downgrade() -> None:
    # Optionally remove the seed data in downgrade
    op.execute("DELETE FROM users WHERE email IN ('motbollox@gmail.com', '80hurtz@gmail.com', 'follower@example.com')")
