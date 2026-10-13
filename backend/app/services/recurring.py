import calendar
from datetime import date, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Frequency, RecurringRule, Transaction
from app.schemas import RecurringIn, UpcomingPayment
from app.services.transactions import check_refs
from app.timeutil import today_bogota

_STEP_DAYS = {Frequency.daily: 1, Frequency.weekly: 7, Frequency.biweekly: 14}


def _add_months(start: date, months: int) -> date:
    """`months` meses después de `start`, conservando el día de `start` (o el último del mes)."""
    year, month0 = divmod(start.year * 12 + start.month - 1 + months, 12)
    month = month0 + 1
    return date(year, month, min(start.day, calendar.monthrange(year, month)[1]))


def next_occurrence(start: date, frequency: Frequency, after: date) -> date:
    """Primera fecha de la regla posterior a `after`.

    Mensual y anual se calculan desde `start`, no desde la fecha anterior: una regla del 31
    cae el 28 en febrero y vuelve al 31 en marzo.
    """
    if frequency in _STEP_DAYS:
        return after + timedelta(days=_STEP_DAYS[frequency])
    step = 1 if frequency == Frequency.monthly else 12
    k = (after.year - start.year) * 12 + after.month - start.month
    n = k // step
    while (candidate := _add_months(start, n * step)) <= after:
        n += 1
    return candidate


def sync_recurring(db: Session, today: date) -> int:
    """Crea los movimientos pendientes de las reglas activas hasta `today`. Idempotente."""
    rules = db.scalars(
        select(RecurringRule).where(RecurringRule.active, RecurringRule.next_run_date <= today)
    ).all()
    created = 0
    for r in rules:
        d = r.next_run_date
        while d <= today and (r.end_date is None or d <= r.end_date):
            exists = db.scalar(
                select(Transaction.id).where(
                    Transaction.recurring_rule_id == r.id, Transaction.date == d
                )
            )
            if exists is None:
                db.add(
                    Transaction(
                        type=r.type, amount=r.amount, date=d, account_id=r.account_id,
                        to_account_id=r.to_account_id, category_id=r.category_id,
                        description=r.description, recurring_rule_id=r.id,
                    )
                )
                created += 1
            d = next_occurrence(r.start_date, r.frequency, d)
        r.next_run_date = d
    try:
        db.commit()
    except IntegrityError:  # otra sincronización simultánea ya creó esos movimientos
        db.rollback()
        return 0
    return created


def upcoming(db: Session, today: date, days: int = 30) -> list[UpcomingPayment]:
    horizon = today + timedelta(days=days)
    items = []
    for r in db.scalars(select(RecurringRule).where(RecurringRule.active)):
        d = r.next_run_date
        while d < today:
            d = next_occurrence(r.start_date, r.frequency, d)
        while d <= horizon and (r.end_date is None or d <= r.end_date):
            items.append(
                UpcomingPayment(
                    rule_id=r.id, date=d, type=r.type, amount=r.amount,
                    description=r.description, account_id=r.account_id,
                    to_account_id=r.to_account_id, category_id=r.category_id,
                )
            )
            d = next_occurrence(r.start_date, r.frequency, d)
    return sorted(items, key=lambda i: (i.date, i.rule_id))


def save_rule(
    db: Session, data: RecurringIn, rule: RecurringRule | None = None, today: date | None = None
) -> RecurringRule:
    check_refs(db, data)
    if rule is None:
        rule = RecurringRule(next_run_date=data.start_date)  # crear con fecha pasada = ponerse al día
    elif (rule.start_date, rule.frequency) != (data.start_date, data.frequency):
        # cambiar el calendario no reescribe el pasado: se retoma desde hoy
        today = today or today_bogota()
        d = data.start_date
        while d < today:
            d = next_occurrence(data.start_date, data.frequency, d)
        rule.next_run_date = d
    for k, v in data.model_dump().items():
        setattr(rule, k, v)
    db.add(rule)
    db.commit()
    return rule


def delete_rule(db: Session, rule: RecurringRule) -> None:
    # lo ya generado es historial real: se conserva, solo se desvincula
    db.execute(update(Transaction).where(Transaction.recurring_rule_id == rule.id).values(recurring_rule_id=None))
    db.delete(rule)
    db.commit()
