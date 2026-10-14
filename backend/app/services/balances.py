from datetime import date

from sqlalchemy import BigInteger, cast, func, select
from sqlalchemy.orm import Session

from app.models import Account, Transaction, TxType


def sum_pesos(column):
    """SUM como entero. Postgres devuelve SUM(bigint) como numeric (Decimal), que la API serializaba como texto."""
    return cast(func.sum(column), BigInteger)


def account_balances(db: Session) -> dict[int, int]:
    """Saldo por cuenta = inicial + ingresos − gastos − transferencias salientes + entrantes.

    Nunca se guarda: se calcula siempre desde los movimientos.
    """
    balances = {a.id: a.initial_balance for a in db.scalars(select(Account))}
    sign = {TxType.income: 1, TxType.expense: -1, TxType.transfer: -1}

    q = select(Transaction.account_id, Transaction.type, sum_pesos(Transaction.amount)).group_by(
        Transaction.account_id, Transaction.type
    )
    for account_id, type_, total in db.execute(q):
        balances[account_id] += sign[type_] * total

    q = (
        select(Transaction.to_account_id, sum_pesos(Transaction.amount))
        .where(Transaction.type == TxType.transfer)
        .group_by(Transaction.to_account_id)
    )
    for account_id, total in db.execute(q):
        balances[account_id] += total
    return balances


def net_worth(balances: dict[int, int]) -> int:
    return sum(balances.values())


def month_totals(db: Session, start: date, end: date) -> tuple[int, int]:
    """(ingresos, gastos) con start <= fecha < end. Las transferencias no cuentan."""
    q = (
        select(Transaction.type, sum_pesos(Transaction.amount))
        .where(Transaction.date >= start, Transaction.date < end)
        .where(Transaction.type.in_([TxType.income, TxType.expense]))
        .group_by(Transaction.type)
    )
    totals = {t: s for t, s in db.execute(q)}
    return totals.get(TxType.income, 0), totals.get(TxType.expense, 0)
