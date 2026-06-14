"""add role to deck_cards

Revision ID: d2a891bc4f10
Revises: b4e7c901fa23
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2a891bc4f10"
down_revision: Union[str, None] = "b4e7c901fa23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deck_cards", sa.Column("role", sa.String(20), nullable=True))


def downgrade() -> None:
    op.drop_column("deck_cards", "role")
