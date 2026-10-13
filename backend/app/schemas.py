import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from app.models import AccountType, CategoryKind, TxType

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Credentials(BaseModel):
    email: str = Field(pattern=EMAIL, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: AccountType
    initial_balance: StrictInt = 0
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


class TransactionIn(BaseModel):
    id: str | None = Field(default=None, max_length=36)
    type: TxType
    amount: StrictInt = Field(gt=0)
    date: dt.date | None = None  # por defecto: hoy en Bogotá
    account_id: int
    to_account_id: int | None = None
    category_id: int | None = None
    description: str | None = Field(default=None, max_length=255)
    tags: list[str] = []

    @model_validator(mode="after")
    def _coherence(self):
        if self.type == TxType.transfer:
            if self.to_account_id is None or self.category_id is not None:
                raise ValueError("Una transferencia necesita cuenta destino y no lleva categoría")
            if self.to_account_id == self.account_id:
                raise ValueError("La cuenta origen y destino deben ser distintas")
        elif self.to_account_id is not None or self.category_id is None:
            raise ValueError("Ingresos y gastos necesitan categoría y no llevan cuenta destino")
        return self


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
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


MONTH = r"^\d{4}-(0[1-9]|1[0-2])$"


class BudgetIn(BaseModel):
    category_id: int
    month: str | None = Field(default=None, pattern=MONTH)  # None = se repite cada mes
    limit_amount: StrictInt = Field(gt=0)
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
