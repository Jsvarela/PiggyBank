import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.models import AccountType, CategoryKind, Frequency, TxType

# Tope de todo monto: 15 cifras (999 billones de pesos). Es menos que 2^53, así que JavaScript lo representa
# exacto (por encima redondea en silencio y mostraría un monto falso), y cabe de sobra en un bigint.
MAX_MONEY = 999_999_999_999_999
EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Credentials(BaseModel):
    email: str = Field(pattern=EMAIL, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class RegisterIn(Credentials):
    invite_code: str | None = Field(default=None, max_length=100)  # no hace falta para el primer usuario


class UserOut(BaseModel):
    id: int
    email: str
    email_verified: bool = False
    is_admin: bool = False


class InviteCreated(BaseModel):
    id: int
    code: str  # solo se muestra al crearla
    expires_at: dt.datetime


class InviteOut(BaseModel):
    id: int
    created_at: dt.datetime
    expires_at: dt.datetime
    status: Literal["pendiente", "usada", "vencida"]
    used_by_email: str | None = None


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: AccountType
    initial_balance: StrictInt = Field(default=0, ge=-MAX_MONEY, le=MAX_MONEY)
    color: str | None = None
    icon: str | None = None
    archived: bool = False


class AccountOut(AccountIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    balance: int = 0


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: CategoryKind
    parent_id: int | None = None
    color: str | None = None
    icon: str | None = None
    archived: bool = False


class CategoryOut(CategoryIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


def check_coherence(m) -> None:
    """Reglas de forma compartidas por movimientos y reglas recurrentes."""
    if m.type == TxType.transfer:
        if m.to_account_id is None or m.category_id is not None:
            raise ValueError("Una transferencia necesita cuenta destino y no lleva categoría")
        if m.to_account_id == m.account_id:
            raise ValueError("La cuenta origen y destino deben ser distintas")
    elif m.to_account_id is not None or m.category_id is None:
        raise ValueError("Ingresos y gastos necesitan categoría y no llevan cuenta destino")


class TransactionIn(BaseModel):
    id: str | None = Field(default=None, max_length=36)
    type: TxType
    amount: StrictInt = Field(gt=0, le=MAX_MONEY)
    date: dt.date | None = None  # por defecto: hoy en Bogotá
    account_id: int
    to_account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    tags: list[str] = []

    @model_validator(mode="after")
    def _coherence(self):
        check_coherence(self)
        return self


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    recurring_rule_id: int | None = None
    goal_id: int | None = None
    type: TxType
    amount: int
    date: dt.date
    account_id: int
    to_account_id: int | None
    category_id: int | None
    description: str | None
    tags: list[str]


class TransactionPage(BaseModel):
    items: list[TransactionOut]
    total: int


class RecurringIn(BaseModel):
    type: TxType
    amount: StrictInt = Field(gt=0, le=MAX_MONEY)
    account_id: int
    to_account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    frequency: Frequency
    start_date: dt.date
    end_date: dt.date | None = None
    active: bool = True

    @model_validator(mode="after")
    def _coherence(self):
        check_coherence(self)
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("La fecha final no puede ser anterior a la inicial")
        return self


class RecurringOut(RecurringIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    next_run_date: dt.date


class UpcomingPayment(BaseModel):
    rule_id: int
    date: dt.date
    type: TxType
    amount: int
    description: str | None
    account_id: int
    to_account_id: int | None
    category_id: int | None


class GoalIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: StrictInt = Field(gt=0, le=MAX_MONEY)
    deadline: dt.date | None = None
    account_id: int | None = None


class GoalOut(GoalIn):
    id: int
    saved: int
    remaining: int
    percent: int
    reached: bool
    monthly_suggested: int | None  # None = sin fecha límite


class ContributionIn(BaseModel):
    amount: StrictInt = Field(gt=0, le=MAX_MONEY)
    from_account_id: int
    date: dt.date | None = None


MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


class BudgetIn(BaseModel):
    category_id: int
    month: str | None = Field(default=None, pattern=MONTH)  # None = se repite cada mes
    limit_amount: StrictInt = Field(gt=0, le=MAX_MONEY)
    alert_threshold: StrictInt = Field(default=80, ge=1, le=100)


class BudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    category_id: int
    month: str | None
    is_default: bool
    limit_amount: int
    alert_threshold: int


class BudgetStatus(BaseModel):
    budget_id: int
    category_id: int
    category_name: str
    is_default: bool
    limit: int
    alert_threshold: int
    spent: int
    percent: int
    remaining: int  # negativo si se pasó
    alert: Literal["ok", "warning", "exceeded"]
    days_left: int


class CategorySpend(BaseModel):
    category_id: int
    name: str
    amount: int
    previous: int
    diff: int


class MonthlyReport(BaseModel):
    month: str
    income: int
    expense: int
    previous_income: int
    previous_expense: int
    categories: list[CategorySpend]


class Dashboard(BaseModel):
    month: str
    accounts: list[AccountOut]
    net_worth: int
    income: int
    expense: int
    recent: list[TransactionOut]
