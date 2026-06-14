"""add match_results table

Revision ID: e3f902cd5a11
Revises: d2a891bc4f10
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3f902cd5a11"
down_revision: Union[str, None] = "d2a891bc4f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=False),
        sa.Column("opponent_arch", sa.String(255), nullable=False),
        sa.Column("result", sa.String(1), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("result IN ('W', 'L', 'D')", name="ck_match_result_value"),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_match_results_deck_id", "match_results", ["deck_id"])
    op.create_index("ix_match_results_opponent_arch", "match_results", ["opponent_arch"])


def downgrade() -> None:
    op.drop_index("ix_match_results_opponent_arch", table_name="match_results")
    op.drop_index("ix_match_results_deck_id", table_name="match_results")
    op.drop_table("match_results")
