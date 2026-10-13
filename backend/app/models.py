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
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Account(Base):
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


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[CategoryKind] = mapped_column(_enum(CategoryKind))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    color: Mapped[str | None] = mapped_column(String(20))
    icon: Mapped[str | None] = mapped_column(String(40))
    archived: Mapped[bool] = mapped_column(default=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
