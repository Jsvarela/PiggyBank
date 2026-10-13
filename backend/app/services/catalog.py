"""CRUD de cuentas y categorías."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Conflict, DomainError, NotFound
from app.models import Account, Budget, Category, Transaction
from app.schemas import AccountIn, CategoryIn


def get_or_404(db: Session, model, id_: int):
    obj = db.get(model, id_)
    if obj is None:
        raise NotFound(f"{model.__name__} {id_} no existe")
    return obj


def _has_transactions(db: Session, *conds) -> bool:
    return db.scalar(select(Transaction.id).where(*conds).limit(1)) is not None


def save_account(db: Session, data: AccountIn, account: Account | None = None) -> Account:
    account = account or Account()
    for k, v in data.model_dump().items():
        setattr(account, k, v)
    db.add(account)
    db.commit()
    return account


def delete_account(db: Session, account: Account) -> None:
    if _has_transactions(
        db, (Transaction.account_id == account.id) | (Transaction.to_account_id == account.id)
    ):
        raise Conflict("La cuenta tiene movimientos: archívala en vez de borrarla")
    db.delete(account)
    db.commit()


def save_category(db: Session, data: CategoryIn, category: Category | None = None) -> Category:
    if data.parent_id is not None:
        parent = get_or_404(db, Category, data.parent_id)
        if parent.parent_id is not None:
            raise DomainError("Solo se permite un nivel de subcategorías")
        if parent.kind != data.kind:
            raise DomainError("La subcategoría debe ser del mismo tipo que la categoría padre")
        if category is not None and parent.id == category.id:
            raise DomainError("Una categoría no puede ser su propio padre")
    category = category or Category()
    for k, v in data.model_dump().items():
        setattr(category, k, v)
    db.add(category)
    db.commit()
    return category


def delete_category(db: Session, category: Category) -> None:
    if (
        _has_transactions(db, Transaction.category_id == category.id)
        or db.scalar(select(Category.id).where(Category.parent_id == category.id).limit(1))
        or db.scalar(select(Budget.id).where(Budget.category_id == category.id).limit(1))
    ):
        raise Conflict(
            "La categoría tiene movimientos, subcategorías o presupuestos: archívala en vez de borrarla"
        )
    db.delete(category)
    db.commit()
