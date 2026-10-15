"""Row Level Security en las tablas con dueño (solo Postgres)

Revision ID: d4e8a1b7c203
Revises: b8c2d4f6a190
Create Date: 2026-10-14

Segunda barrera de aislamiento dentro de la base de datos (ver app/rls.py). En SQLite no hace nada.
Las migraciones futuras que lean o cambien DATOS de estas tablas deben correr con un rol que se salte RLS
(MIGRATION_DATABASE_URL); las que solo cambian el esquema no se ven afectadas.
"""
from collections.abc import Sequence

from alembic import op

from app import rls

revision: str = "d4e8a1b7c203"
down_revision: str | Sequence[str] | None = "b8c2d4f6a190"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        rls.enable(op.get_bind())


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        rls.disable(op.get_bind())
