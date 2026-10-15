"""prestamos: abonos parciales y deudas propias

Revision ID: b8c2d4f6a190
Revises: a3d5b8e1f607
Create Date: 2026-10-14

Los préstamos ya marcados como pagados pasan a tener todo recibido, para que `paid` siga siendo coherente.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c2d4f6a190"
down_revision: str | Sequence[str] | None = "a3d5b8e1f607"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("loans") as batch:
        batch.add_column(sa.Column("direction", sa.String(10), nullable=False, server_default="lent"))
        batch.add_column(sa.Column("received", sa.BigInteger(), nullable=False, server_default="0"))
        batch.drop_constraint("loan_positive", type_="check")
        batch.create_check_constraint("loan_positive", "amount > 0 AND expected_amount > 0 AND received >= 0")
    op.execute(sa.text("UPDATE loans SET received = expected_amount WHERE paid"))


def downgrade() -> None:
    with op.batch_alter_table("loans") as batch:
        batch.drop_constraint("loan_positive", type_="check")
        batch.create_check_constraint("loan_positive", "amount > 0 AND expected_amount > 0")
        batch.drop_column("received")
        batch.drop_column("direction")
