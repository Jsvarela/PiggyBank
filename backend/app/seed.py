"""Categorías por defecto. Con --demo agrega cuentas y movimientos de ejemplo.

Uso: uv run python -m app.seed [--demo]
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Account, AccountType, Category, CategoryKind, Transaction, TxType, User
from app.security import hash_password
from app.timeutil import today_bogota

EXPENSE = ["Comida", "Transporte", "Vivienda", "Servicios", "Universidad", "Ocio", "Salud", "Suscripciones", "Otros"]
INCOME = ["Salario", "Freelance", "Regalos", "Otros ingresos"]


def seed_categories(db: Session) -> None:
    if db.scalar(select(Category.id).limit(1)):
        return
    db.add_all(
        [Category(name=n, kind=CategoryKind.expense) for n in EXPENSE]
        + [Category(name=n, kind=CategoryKind.income) for n in INCOME]
    )
    db.commit()


def seed_demo(db: Session) -> None:
    if db.scalar(select(Account.id).limit(1)):
        return
    cuentas = {
        "Efectivo": Account(name="Efectivo", type=AccountType.cash, initial_balance=80_000),
        "Bancolombia": Account(name="Bancolombia", type=AccountType.bank, initial_balance=1_500_000),
        "Nequi": Account(name="Nequi", type=AccountType.digital_wallet, initial_balance=0),
        "Tarjeta": Account(name="Tarjeta de crédito", type=AccountType.credit_card, initial_balance=0),
    }
    db.add_all(cuentas.values())
    db.flush()
    cat = {c.name: c.id for c in db.scalars(select(Category))}
    hoy = today_bogota()
    db.add_all(
        [
            Transaction(type=TxType.income, amount=2_000_000, date=hoy, account_id=cuentas["Bancolombia"].id, category_id=cat["Salario"], description="Pago mensual"),
            Transaction(type=TxType.expense, amount=18_000, date=hoy, account_id=cuentas["Efectivo"].id, category_id=cat["Comida"], description="Almuerzo"),
            Transaction(type=TxType.expense, amount=45_000, date=hoy, account_id=cuentas["Tarjeta"].id, category_id=cat["Ocio"], description="Cine"),
            Transaction(type=TxType.transfer, amount=100_000, date=hoy, account_id=cuentas["Bancolombia"].id, to_account_id=cuentas["Nequi"].id, description="Pasar a Nequi"),
        ]
    )
    db.commit()


def _owner(session: Session) -> User:
    """Los datos tienen dueño: se siembran para el primer usuario (o uno de desarrollo si aún no hay ninguno)."""
    user = session.scalar(select(User).order_by(User.id))
    if user is None:
        user = User(email="demo@localhost.test", password_hash=hash_password("demo-local-12345"), is_admin=True)
        session.add(user)
        session.commit()
        print("Creé el usuario de desarrollo demo@localhost.test (clave en app/seed.py)")
    return user


if __name__ == "__main__":
    with SessionLocal() as session:
        session.info["user_id"] = _owner(session).id
        seed_categories(session)
        if "--demo" in sys.argv:
            seed_demo(session)
