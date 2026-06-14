"""add_tags_to_decks

Revision ID: b4e7c901fa23
Revises: 7df3815aee38
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4e7c901fa23"
down_revision: Union[str, None] = "7df3815aee38"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("decks", sa.Column("tags", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("decks", "tags")
