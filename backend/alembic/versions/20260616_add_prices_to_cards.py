"""add_prices_to_cards

Revision ID: f1a02de6b733
Revises: e3f902cd5a11
Create Date: 2026-06-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f1a02de6b733"
down_revision: Union[str, None] = "e3f902cd5a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cards", sa.Column("cardmarket_price", sa.Float(), nullable=True))
    op.add_column("cards", sa.Column("tcgplayer_price", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("cards", "tcgplayer_price")
    op.drop_column("cards", "cardmarket_price")
