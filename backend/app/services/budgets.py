from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Budget, Category, CategoryKind, Transaction, TxType
from app.schemas import BudgetIn, BudgetStatus, CategorySpend, MonthlyReport, TrendPoint
from app.services.balances import month_totals, sum_pesos
from app.services.catalog import get_or_404
from app.timeutil import month_range


def parse_month(month: str) -> date:
    try:
        year, mon = month.split("-")
        return date(int(year), int(mon), 1)
    except ValueError:
        raise DomainError("Mes inválido: usa el formato AAAA-MM") from None


def save_budget(db: Session, data: BudgetIn) -> Budget:
    """Upsert por (categoría, mes | por defecto): guardar dos veces no duplica."""
    category = get_or_404(db, Category, data.category_id)
    if category.kind != CategoryKind.expense:
        raise DomainError("Solo se puede presupuestar categorías de gasto")
    budget = db.scalar(
        select(Budget).where(
            Budget.category_id == data.category_id,
            Budget.month.is_(None) if data.month is None else Budget.month == data.month,
        )
    ) or Budget(category_id=data.category_id, month=data.month, is_default=data.month is None)
    budget.limit_amount = data.limit_amount
    budget.alert_threshold = data.alert_threshold
    db.add(budget)
    db.commit()
    return budget


def _direct_spend(db: Session, start: date, end: date) -> dict[int, int]:
    q = (
        select(Transaction.category_id, sum_pesos(Transaction.amount))
        .where(Transaction.type == TxType.expense, Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.category_id)
    )
    return {cid: total for cid, total in db.execute(q)}


def _days_left(first: date, nxt: date, today: date) -> int:
    last = nxt - timedelta(days=1)
    if today < first:
        return (nxt - first).days  # mes futuro: el mes completo
    return max((last - today).days, 0)


def budget_status(db: Session, month: str, today: date) -> list[BudgetStatus]:
    first, nxt = month_range(parse_month(month))
    spend = _direct_spend(db, first, nxt)
    categories = {c.id: c for c in db.scalars(select(Category))}
    children: dict[int, list[int]] = defaultdict(list)
    for c in categories.values():
        if c.parent_id:
            children[c.parent_id].append(c.id)

    # el presupuesto del mes reemplaza al "por defecto" de la misma categoría
    chosen: dict[int, Budget] = {}
    for b in db.scalars(select(Budget).order_by(Budget.is_default.desc())):
        if b.is_default or b.month == month:
            chosen[b.category_id] = b

    items = []
    for b in chosen.values():
        spent = spend.get(b.category_id, 0) + sum(spend.get(c, 0) for c in children[b.category_id])
        pct = spent * 100 // b.limit_amount
        alert = "exceeded" if spent > b.limit_amount else "warning" if pct >= b.alert_threshold else "ok"
        items.append(
            BudgetStatus(
                budget_id=b.id,
                category_id=b.category_id,
                category_name=categories[b.category_id].name,
                is_default=b.is_default,
                limit=b.limit_amount,
                alert_threshold=b.alert_threshold,
                spent=spent,
                percent=pct,
                remaining=b.limit_amount - spent,
                alert=alert,
                days_left=_days_left(first, nxt, today),
            )
        )
    return sorted(items, key=lambda i: i.category_name)


def trend(db: Session, month: str, months: int) -> list[TrendPoint]:
    """Ingresos y gastos de los últimos `months` meses, terminando en `month` (el más viejo primero)."""
    out, first = [], month_range(parse_month(month))[0]
    for _ in range(months):
        income, expense = month_totals(db, *month_range(first))
        out.append(TrendPoint(month=first.strftime("%Y-%m"), income=income, expense=expense))
        first = month_range(first - timedelta(days=1))[0]
    return out[::-1]


def monthly_report(db: Session, month: str) -> MonthlyReport:
    first, nxt = month_range(parse_month(month))
    prev_first, prev_nxt = month_range(first - timedelta(days=1))
    categories = {c.id: c for c in db.scalars(select(Category))}

    def by_top_level(start: date, end: date) -> dict[int, int]:
        out: dict[int, int] = defaultdict(int)
        for cid, amount in _direct_spend(db, start, end).items():
            out[categories[cid].parent_id or cid] += amount
        return out

    now, before = by_top_level(first, nxt), by_top_level(prev_first, prev_nxt)
    rows = [
        CategorySpend(
            category_id=cid,
            name=categories[cid].name,
            amount=now.get(cid, 0),
            previous=before.get(cid, 0),
            diff=now.get(cid, 0) - before.get(cid, 0),
        )
        for cid in set(now) | set(before)
    ]
    income, expense = month_totals(db, first, nxt)
    prev_income, prev_expense = month_totals(db, prev_first, prev_nxt)
    return MonthlyReport(
        month=month,
        income=income,
        expense=expense,
        previous_income=prev_income,
        previous_expense=prev_expense,
        categories=sorted(rows, key=lambda r: -r.amount),
    )
