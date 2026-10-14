"""multiusuario: dueño en cada dato, administrador e invitaciones

Revision ID: c7a1e9d04b52
Revises: f2e66f436831
Create Date: 2026-10-14

Los datos que ya existen (de la versión de un solo usuario) pasan a ser del único usuario que haya, que además
queda como administrador. En 3 pasos para no perder nada: agregar la columna vacía -> asignar dueño -> hacerla obligatoria.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c7a1e9d04b52"
down_revision: str | Sequence[str] | None = "f2e66f436831"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OWNED = ["accounts", "categories", "transactions", "budgets", "recurring_rules", "savings_goals"]


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.create_table(
        "invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("used_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )

    owner = op.get_bind().execute(sa.text("SELECT id FROM users ORDER BY id LIMIT 1")).scalar()
    if owner is not None:
        op.execute(sa.text("UPDATE users SET is_admin = :yes WHERE id = :id").bindparams(yes=True, id=owner))

    for table in OWNED:
        with op.batch_alter_table(table) as batch:
            batch.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        if owner is not None:
            op.execute(sa.text(f"UPDATE {table} SET user_id = :owner").bindparams(owner=owner))  # noqa: S608
        # si quedara alguna fila sin dueño (no debería), NOT NULL falla y la migración se revierte entera
        with op.batch_alter_table(table) as batch:
            batch.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
            batch.create_foreign_key(f"fk_{table}_user", "users", ["user_id"], ["id"])
            batch.create_index(f"ix_{table}_user_id", ["user_id"])


def downgrade() -> None:
    for table in reversed(OWNED):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_user_id")
            batch.drop_constraint(f"fk_{table}_user", type_="foreignkey")
            batch.drop_column("user_id")
    op.drop_table("invites")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("is_admin")
