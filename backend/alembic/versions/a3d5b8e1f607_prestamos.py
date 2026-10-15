"""prestamos: dinero que le prestaste a otras personas

Revision ID: a3d5b8e1f607
Revises: c7a1e9d04b52
Create Date: 2026-10-14
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3d5b8e1f607"
down_revision: str | Sequence[str] | None = "c7a1e9d04b52"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("person", sa.String(100), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("expected_amount", sa.BigInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("paid", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0 AND expected_amount > 0", name="loan_positive"),
    )
    op.create_index("ix_loans_user_id", "loans", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_loans_user_id", table_name="loans")
    op.drop_table("loans")
