"""add_cdb_sync_type

Revision ID: 7df3815aee38
Revises: 80311f74b4a2
Create Date: 2026-06-11 19:29:59.749771

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7df3815aee38'
down_revision: Union[str, None] = '80311f74b4a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE synctype ADD VALUE IF NOT EXISTS 'cdb'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; a full rebuild would be needed.
    pass
