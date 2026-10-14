import csv
import datetime as dt
import io
from typing import Literal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Account, Budget, Category, RecurringRule, SavingsGoal, Transaction
from app.schemas import (
    AccountIn,
    BudgetIn,
    CategoryIn,
    GoalIn,
    RecurringIn,
    TransactionIn,
)

_ORM = ConfigDict(from_attributes=True)


# Los ids del respaldo solo sirven para enlazar filas entre sí; al restaurar se crean ids nuevos.
class BAccount(AccountIn):
    model_config = _ORM
    id: int


class BCategory(CategoryIn):
    model_config = _ORM
    id: int


class BGoal(GoalIn):
    model_config = _ORM
    id: int


class BRule(RecurringIn):
    model_config = _ORM
    id: int
    next_run_date: dt.date


class BTransaction(TransactionIn):
    model_config = _ORM
    recurring_rule_id: int | None = None
    goal_id: int | None = None


class BBudget(BudgetIn):
    model_config = _ORM


class Backup(BaseModel):
    version: Literal[1]
    accounts: list[BAccount]
    categories: list[BCategory]
    goals: list[BGoal]
    recurring_rules: list[BRule]
    transactions: list[BTransaction]
    budgets: list[BBudget]


def export_backup(db: Session) -> Backup:
    def rows(model, schema):
        return [schema.model_validate(r) for r in db.scalars(select(model).order_by(model.id))]

    return Backup(
        version=1,
        accounts=rows(Account, BAccount),
        categories=rows(Category, BCategory),
        goals=rows(SavingsGoal, BGoal),
        recurring_rules=rows(RecurringRule, BRule),
        transactions=[BTransaction.model_validate(t) for t in db.scalars(select(Transaction).order_by(Transaction.date, Transaction.created_at))],
        budgets=rows(Budget, BBudget),
    )


def _ref(ids: dict[int, int], old: int | None, what: str) -> int | None:
    if old is None:
        return None
    if old not in ids:
        raise DomainError(f"El respaldo referencia {what} {old} que no existe")
    return ids[old]


def wipe_data(db: Session) -> None:
    """Borra todos los datos financieros (no el usuario), en orden de dependencias. No hace commit."""
    for model in (Transaction, Budget, RecurringRule, SavingsGoal, Category, Account):
        db.execute(delete(model))


def restore_backup(db: Session, b: Backup) -> None:
    """Reemplaza TODOS los datos por los del respaldo, en una sola transacción."""
    try:
        wipe_data(db)

        def add(obj):
            db.add(obj)
            db.flush()
            return obj.id

        acc = {a.id: add(Account(**a.model_dump(exclude={"id"}))) for a in b.accounts}
        cat: dict[int, int] = {}
        # padres primero: una subcategoría solo puede apuntar a una categoría ya creada
        for c in sorted(b.categories, key=lambda c: c.parent_id is not None):
            data = c.model_dump(exclude={"id"})
            data["parent_id"] = _ref(cat, c.parent_id, "la categoría")
            cat[c.id] = add(Category(**data))
        goal = {}
        for g in b.goals:
            data = g.model_dump(exclude={"id"})
            data["account_id"] = _ref(acc, g.account_id, "la cuenta")
            goal[g.id] = add(SavingsGoal(**data))
        rule = {}
        for r in b.recurring_rules:
            data = r.model_dump(exclude={"id"})
            data.update(
                account_id=_ref(acc, r.account_id, "la cuenta"),
                to_account_id=_ref(acc, r.to_account_id, "la cuenta"),
                category_id=_ref(cat, r.category_id, "la categoría"),
            )
            rule[r.id] = add(RecurringRule(**data))
        for t in b.transactions:
            data = t.model_dump()
            data.update(
                account_id=_ref(acc, t.account_id, "la cuenta"),
                to_account_id=_ref(acc, t.to_account_id, "la cuenta"),
                category_id=_ref(cat, t.category_id, "la categoría"),
                recurring_rule_id=_ref(rule, t.recurring_rule_id, "la regla"),
                goal_id=_ref(goal, t.goal_id, "la meta"),
            )
            if data["date"] is None:
                raise DomainError("Hay un movimiento sin fecha en el respaldo")
            if data["id"] is None:
                del data["id"]
            db.add(Transaction(**data))
        for bd in b.budgets:
            data = bd.model_dump()
            data.update(category_id=_ref(cat, bd.category_id, "la categoría"), is_default=bd.month is None)
            db.add(Budget(**data))
        db.commit()
    except Exception:
        db.rollback()
        raise


_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def _safe(value: str) -> str:
    # una celda que empieza con = + - @ se ejecuta como fórmula al abrir el CSV en Excel
    return "'" + value if value.startswith(_FORMULA) else value


def transactions_csv(db: Session) -> str:
    accounts = {a.id: a.name for a in db.scalars(select(Account))}
    categories = {c.id: c.name for c in db.scalars(select(Category))}
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["fecha", "tipo", "monto", "cuenta", "cuenta_destino", "categoria", "descripcion", "etiquetas"])
    for t in db.scalars(select(Transaction).order_by(Transaction.date, Transaction.created_at)):
        w.writerow([
            t.date.isoformat(), t.type.value, t.amount, _safe(accounts[t.account_id]),
            _safe(accounts.get(t.to_account_id, "")), _safe(categories.get(t.category_id, "")),
            _safe(t.description or ""), _safe(",".join(t.tags or [])),
        ])
    return out.getvalue()
