from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Account, Category, Transaction, TxType
from app.schemas import TransactionIn
from app.services.catalog import get_or_404
from app.timeutil import today_bogota


def check_refs(db: Session, data) -> None:
    """Cuentas y categoría existen y la categoría es del tipo del movimiento (o regla)."""
    get_or_404(db, Account, data.account_id)
    if data.to_account_id is not None:
        get_or_404(db, Account, data.to_account_id)
    if data.category_id is not None:
        category = get_or_404(db, Category, data.category_id)
        if category.kind.value != data.type.value:
            raise DomainError("La categoría no corresponde al tipo de movimiento")


def save_transaction(
    db: Session, data: TransactionIn, tx: Transaction | None = None
) -> Transaction:
    check_refs(db, data)

    values = data.model_dump(exclude={"id"})
    values["date"] = data.date or today_bogota()
    if tx is None:
        tx = Transaction(**({"id": data.id} if data.id else {}))
    for k, v in values.items():
        setattr(tx, k, v)
    db.add(tx)
    db.commit()
    return tx


def save_transactions(db: Session, items: list[TransactionIn]) -> int:
    """Crea varios movimientos de una vez: o entran todos o no entra ninguno."""
    for data in items:
        check_refs(db, data)
    for data in items:
        values = data.model_dump(exclude={"id"})
        values["date"] = data.date or today_bogota()
        db.add(Transaction(**({"id": data.id} if data.id else {}), **values))
    db.commit()
    return len(items)


def list_transactions(
    db: Session,
    *,
    start: date | None = None,
    end: date | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    type_: TxType | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Transaction], int]:
    conds = []
    if start:
        conds.append(Transaction.date >= start)
    if end:
        conds.append(Transaction.date <= end)
    if account_id:
        conds.append(or_(Transaction.account_id == account_id, Transaction.to_account_id == account_id))
    if category_id:
        conds.append(Transaction.category_id == category_id)
    if type_:
        conds.append(Transaction.type == type_)
    if q:
        conds.append(Transaction.description.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(Transaction).where(*conds)) or 0
    items = db.scalars(
        select(Transaction)
        .where(*conds)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return list(items), total
