import enum
import uuid
from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.tenancy import Owned


def _now() -> datetime:
    return datetime.now(UTC)


def _enum(cls: type[enum.Enum]) -> Enum:
    # guarda el valor ("expense"), no el nombre del miembro
    return Enum(cls, native_enum=False, length=20, values_callable=lambda e: [m.value for m in e])


class AccountType(str, enum.Enum):
    cash = "cash"
    bank = "bank"
    digital_wallet = "digital_wallet"
    credit_card = "credit_card"
    savings = "savings"


class CategoryKind(str, enum.Enum):
    income = "income"
    expense = "expense"


class TxType(str, enum.Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"


class Frequency(str, enum.Enum):
    daily = "daily"
    weekly = "weekly"
    biweekly = "biweekly"  # cada 14 días
    monthly = "monthly"
    yearly = "yearly"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # sube cada vez que se debe invalidar toda sesión abierta (ver security.py)
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
    is_admin: Mapped[bool] = mapped_column(default=False, server_default=false())  # puede invitar gente


class Invite(Base):
    """Invitación de un solo uso para crear una cuenta. El código se muestra una vez; aquí solo su hash."""

    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    used_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class Account(Owned, Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[AccountType] = mapped_column(_enum(AccountType))
    # Saldo de partida en COP (entero). El saldo actual se CALCULA, ver services/balances.py.
    initial_balance: Mapped[int] = mapped_column(BigInteger, default=0)
    color: Mapped[str | None] = mapped_column(String(20))
    icon: Mapped[str | None] = mapped_column(String(40))
    archived: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Category(Owned, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[CategoryKind] = mapped_column(_enum(CategoryKind))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    color: Mapped[str | None] = mapped_column(String(20))
    icon: Mapped[str | None] = mapped_column(String(40))
    archived: Mapped[bool] = mapped_column(default=False)


class Budget(Owned, Base):
    """Límite mensual de gasto por categoría.

    `is_default` = se repite cada mes; una fila con `month` ("YYYY-MM") reemplaza al default
    solo en ese mes. La unicidad (categoría, mes|default) la garantiza el upsert del servicio.
    """

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("limit_amount > 0", name="limit_positive"),
        CheckConstraint("alert_threshold BETWEEN 1 AND 100", name="threshold_range"),
        CheckConstraint(
            "(is_default AND month IS NULL) OR (NOT is_default AND month IS NOT NULL)",
            name="default_or_month",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    month: Mapped[str | None] = mapped_column(String(7))
    is_default: Mapped[bool] = mapped_column(default=False)
    limit_amount: Mapped[int] = mapped_column(BigInteger)
    alert_threshold: Mapped[int] = mapped_column(default=80)


class RecurringRule(Owned, Base):
    """Plantilla de movimiento que se repite. Las fechas se calculan desde `start_date`."""

    __tablename__ = "recurring_rules"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "(type = 'transfer' AND to_account_id IS NOT NULL AND category_id IS NULL"
            " AND to_account_id != account_id)"
            " OR (type != 'transfer' AND to_account_id IS NULL AND category_id IS NOT NULL)",
            name="type_coherence",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[TxType] = mapped_column(_enum(TxType))
    amount: Mapped[int] = mapped_column(BigInteger)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    description: Mapped[str | None] = mapped_column(String(255))
    frequency: Mapped[Frequency] = mapped_column(_enum(Frequency))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_run_date: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(default=True)


class SavingsGoal(Owned, Base):
    __tablename__ = "savings_goals"
    __table_args__ = (CheckConstraint("target_amount > 0", name="target_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[int] = mapped_column(BigInteger)
    deadline: Mapped[date | None] = mapped_column(Date)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Transaction(Owned, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        # una regla no puede generar dos movimientos el mismo día (idempotencia a nivel de BD)
        UniqueConstraint("recurring_rule_id", "date", name="uq_tx_rule_date"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "(type = 'transfer' AND to_account_id IS NOT NULL AND category_id IS NULL"
            " AND to_account_id != account_id)"
            " OR (type != 'transfer' AND to_account_id IS NULL AND category_id IS NOT NULL)",
            name="type_coherence",
        ),
        Index("ix_tx_date", "date"),
        Index("ix_tx_account_date", "account_id", "date"),
        Index("ix_tx_category_date", "category_id", "date"),
    )

    # UUID como texto: el cliente puede generarlo (modo offline, Fase 5).
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[TxType] = mapped_column(_enum(TxType))
    amount: Mapped[int] = mapped_column(BigInteger)
    date: Mapped[date] = mapped_column(Date)  # día del gasto, sin zona horaria
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    to_account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    description: Mapped[str | None] = mapped_column(String(255))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    recurring_rule_id: Mapped[int | None] = mapped_column(ForeignKey("recurring_rules.id"))
    goal_id: Mapped[int | None] = mapped_column(ForeignKey("savings_goals.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
