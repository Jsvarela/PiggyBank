"""Datos del PEOR CASO para probar la interfaz (solo desarrollo). Prueba de regresión visual.

Crea (o REEMPLAZA) todo en la base indicada por DATABASE_URL: úsalo solo con una base desechable.

    DATABASE_URL=sqlite:///./worst.db uv run python -m app.seed_worst [worst|empty|one|huge]

Entrada: worst@localhost.test (la contraseña está más abajo; es solo para esta base local).
Los valores son realistas y respetan los límites del esquema (nombres 100, descripción 255 caracteres).
"""

import random
import sys
from datetime import timedelta

from app.db import Base, SessionLocal, engine
from app.models import (
    Account,
    AccountType,
    Budget,
    Category,
    CategoryKind,
    Frequency,
    Loan,
    RecurringRule,
    SavingsGoal,
    Transaction,
    TxType,
    User,
)
from app.security import hash_password
from app.seed import seed_categories
from app.tenancy import bind_user
from app.timeutil import today_bogota

EMAIL, PASSWORD = "worst@localhost.test", "worst-case-local-123"

LONG_ACCOUNT = "Cuenta de ahorros Bancolombia Preferencial Plus Nómina Empresa Internacional S.A.S."
LONG_CARD = "Tarjeta de crédito Visa Gold Davivienda — Cliente Premium con millas LifeMiles"
LONG_CATEGORY = "Servicios públicos (agua, luz, gas, alcantarillado, aseo, internet y televisión)"
LONG_SUBCATEGORY = "Internet y televisión por cable con decodificador adicional y servicio técnico"
LONG_INCOME_CATEGORY = "Ingresos extraordinarios por venta de activos fijos y liquidaciones"
LONG_GOAL = "Viaje familiar a Cartagena, San Andrés y el Eje Cafetero en diciembre con toda la familia"
# 255 caracteres justos, con espacios (debe partirse en líneas)
LONG_TEXT = ("Pago de la cuota extraordinaria de administración del conjunto residencial correspondiente al "
             "semestre anterior, más intereses de mora, retroactivo de servicios comunes y ajuste por la "
             "reliquidación del año pasado según acta de asamblea extraordinaria número 14.")[:255]
# sin espacios: no hay dónde partirlo
LONG_PERSON = "María Fernanda de los Ángeles Rodríguez-Hernández de la Vega y Montoya (prima de Cali)"  # 90
EMAIL_PERSON = "juan.pablo.rodriguez.montoya.gutierrez@correo-empresarial-internacional.com.co"
UNBREAKABLE = "PSE-REF-9f8e7d6c5b4a4c3d8e2f1a0b9c8d7e6f-AUTORIZACION-BANCOLOMBIA-0001234567890123456789"


def build_worst(db) -> None:
    today = today_bogota()
    acc = {}

    def account(key, name, type_, balance, archived=False):
        a = Account(name=name, type=type_, initial_balance=balance, archived=archived)
        db.add(a)
        db.flush()
        acc[key] = a

    account("long", LONG_ACCOUNT, AccountType.bank, 12_345_678_900)  # saldo enorme
    account("one", "A", AccountType.cash, 0)  # una letra, saldo cero
    account("card", LONG_CARD, AccountType.credit_card, -9_876_543_210)  # deuda enorme
    account("emoji", "Ñandú 🦊", AccountType.digital_wallet, 1)
    account("old", "Cuenta vieja", AccountType.savings, 500_000, archived=True)  # archivada con saldo
    account("cash", "Efectivo", AccountType.cash, 80_000)

    cat = {c.name: c for c in db.query(Category)}
    extra = {}
    for key, name, kind, parent in [
        ("serv", LONG_CATEGORY, CategoryKind.expense, None),
        ("net", LONG_SUBCATEGORY, CategoryKind.expense, "serv"),
        ("burger", "🍔 Comida rápida", CategoryKind.expense, None),
        ("inc", LONG_INCOME_CATEGORY, CategoryKind.income, None),
    ]:
        c = Category(name=name, kind=kind, parent_id=extra[parent].id if parent else None)
        db.add(c)
        db.flush()
        extra[key] = c

    def tx(days_ago, type_, amount, account_key, category=None, description=None, to=None, goal=None):
        db.add(Transaction(
            type=type_, amount=amount, date=today - timedelta(days=days_ago), account_id=acc[account_key].id,
            to_account_id=acc[to].id if to else None, category_id=category.id if category else None,
            description=description, goal_id=goal.id if goal else None,
        ))

    # Los primeros renglones son los que se ven: repartir los fallos entre ellos.
    tx(0, TxType.expense, 12_345_678_900, "long", extra["serv"], LONG_TEXT)  # monto enorme + texto de 255
    tx(0, TxType.expense, 999_999_999, "card", extra["net"], UNBREAKABLE)  # sin espacios
    tx(1, TxType.income, 1, "one", extra["inc"], None)  # monto 1, sin descripción: usa la categoría larga
    tx(1, TxType.expense, 45_300, "emoji", extra["burger"], "<script>alert(1)</script> &amp; **negrita**")
    tx(2, TxType.transfer, 7_500_000, "long", to="card", description=None)  # origen y destino larguísimos
    tx(2, TxType.expense, 18_000, "cash", cat["Comida"], "  Almuerzo   con   espacios  ")
    tx(3, TxType.expense, 250, "cash", cat["Transporte"], "Bus")
    tx(400, TxType.income, 5_000_000, "long", cat["Salario"], "Fecha vieja")
    tx(-30, TxType.expense, 90_000, "cash", cat["Ocio"], "Fecha futura")  # días negativos = futuro
    for i in range(12):  # un grupo de filas normales para que haya lista
        tx(4 + i, TxType.expense, 10_000 + i * 1_234, "cash", cat["Comida"], f"Compra {i + 1}")

    # Presupuestos: cada estado y los extremos de porcentaje
    for category, limit in [(extra["serv"], 1_000_000), (cat["Comida"], 100), (extra["burger"], 45_300),
                            (cat["Ocio"], 90_000_000), (cat["Transporte"], 1)]:
        db.add(Budget(category_id=category.id, month=None, is_default=True, limit_amount=limit))

    # Metas: enorme, cumplida con sobrante, sin cuenta, vencida
    big = SavingsGoal(name=LONG_GOAL, target_amount=50_000_000_000, deadline=today + timedelta(days=45),
                      account_id=acc["emoji"].id)
    done = SavingsGoal(name="Moto", target_amount=1, deadline=None, account_id=acc["emoji"].id)
    over = SavingsGoal(name="Fondo de emergencia", target_amount=100_000, deadline=None, account_id=acc["emoji"].id)
    no_acc = SavingsGoal(name="Meta sin cuenta", target_amount=2_000_000, deadline=None, account_id=None)
    late = SavingsGoal(name="Vencida", target_amount=1_000_000, deadline=today - timedelta(days=90),
                       account_id=acc["emoji"].id)
    db.add_all([big, done, over, no_acc, late])
    db.flush()
    tx(5, TxType.transfer, 5_000, "cash", to="emoji", goal=big, description="Aporte")
    tx(5, TxType.transfer, 3, "cash", to="emoji", goal=done, description="Aporte")
    tx(5, TxType.transfer, 150_000, "cash", to="emoji", goal=over, description="Aporte")

    # Recurrentes: una diaria llena los "próximos 30 días"; textos extremos; una pausada
    for desc, amount, freq, active in [
        ("Café", 5_000, Frequency.daily, True),
        (LONG_TEXT, 12_345_678_900, Frequency.weekly, True),
        (UNBREAKABLE, 1, Frequency.monthly, True),
        ("Suscripción pausada", 29_900, Frequency.monthly, False),
    ]:
        db.add(RecurringRule(type=TxType.expense, amount=amount, account_id=acc["cash"].id,
                             category_id=cat["Suscripciones"].id, description=desc, frequency=freq,
                             start_date=today, next_run_date=today, active=active))


def build_loans_worst(db) -> None:
    today = today_bogota()
    day = lambda n: today + timedelta(days=n)
    big = 50_000_000_000
    # (persona, prestado, total, recibido, fecha, nota, dirección)
    rows = [
        (LONG_PERSON, 1_234_567_890, 1_345_000_000, 400_000_000, day(-400), LONG_TEXT, "lent"),  # nombre largo, vencido hace más de un año
        (EMAIL_PERSON, big, big, big - 1, day(3), UNBREAKABLE, "lent"),  # monto enorme, falta 1 peso, nota sin espacios
        ("J", 1, 1, 0, None, None, "lent"),  # una letra, un peso, sin fecha
        ("Tío Beto 🧑‍🔧", 100_000, 90_000, 0, day(0), None, "lent"),  # emoji, le cobras menos de lo prestado, vence hoy
        ("Camila", big, big, 1, day(30), "Casi nada abonado", "lent"),  # 1 peso de 50 mil millones: barra al 0 %
        ("Pagado hace rato", 200_000, 200_000, 200_000, day(-60), None, "lent"),  # ya pagado
        ("Ana", 80_000, 80_000, 0, day(10), None, "lent"),
        ("Pedro", 80_000, 80_000, 0, day(11), None, "lent"),  # más de 3 pendientes: Inicio tiene que cortar la lista
        (LONG_PERSON, 5_000_000, 5_500_000, 0, day(-5), "Arriendo del local", "borrowed"),
        (EMAIL_PERSON, big, big, 0, None, None, "borrowed"),
        ("Mamá", 300_000, 300_000, 150_000, day(20), None, "borrowed"),
        ("Deuda saldada", 50_000, 50_000, 50_000, None, None, "borrowed"),
    ]
    for person, amount, expected, received, due, note, direction in rows:
        db.add(Loan(person=person, amount=amount, expected_amount=expected, received=received, due_date=due, note=note,
                    direction=direction, paid=received >= expected))


def build_one(db) -> None:
    today = today_bogota()
    a = Account(name="Efectivo", type=AccountType.cash, initial_balance=100_000)
    db.add(a)
    db.flush()
    comida = db.query(Category).filter_by(name="Comida").one()
    db.add(Transaction(type=TxType.expense, amount=18_000, date=today, account_id=a.id, category_id=comida.id,
                       description="Almuerzo"))
    db.add(Budget(category_id=comida.id, month=None, is_default=True, limit_amount=100_000))
    db.add(SavingsGoal(name="Viaje", target_amount=1_000_000, account_id=a.id))
    db.add(Loan(person="Camila", amount=100_000, expected_amount=100_000, direction="lent"))
    db.add(RecurringRule(type=TxType.expense, amount=29_900, account_id=a.id, category_id=comida.id,
                         description="Netflix", frequency=Frequency.monthly, start_date=today, next_run_date=today))


def build_huge(db, n: int = 1500) -> None:
    rng = random.Random(7)
    today = today_bogota()
    accounts = []
    for name in ("Efectivo", "Bancolombia", "Nequi"):
        a = Account(name=name, type=AccountType.bank, initial_balance=1_000_000)
        db.add(a)
        accounts.append(a)
    db.flush()
    cats = db.query(Category).filter_by(kind=CategoryKind.expense).all()
    for i in range(n):
        db.add(Transaction(type=TxType.expense, amount=rng.randint(1_000, 400_000), date=today - timedelta(days=rng.randint(0, 730)),
                           account_id=rng.choice(accounts).id, category_id=rng.choice(cats).id,
                           description=f"Movimiento {i + 1}"))
    for i in range(200):  # una lista de préstamos sin paginar
        db.add(Loan(person=f"Persona {i + 1}", amount=50_000, expected_amount=55_000, received=rng.choice([0, 0, 20_000]),
                    direction=rng.choice(["lent", "borrowed"]), due_date=today + timedelta(days=rng.randint(-30, 90))))


def build_worst_all(db) -> None:
    build_worst(db)
    build_loans_worst(db)


BUILDERS = {"worst": build_worst_all, "empty": lambda db: None, "one": build_one, "huge": build_huge}


def main(state: str) -> None:
    Base.metadata.drop_all(engine)  # base desechable de desarrollo: se recrea de cero, sin Alembic
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        user = User(email=EMAIL, password_hash=hash_password(PASSWORD), is_admin=True)
        db.add(user)
        db.commit()
        bind_user(db, user.id)  # todo lo que sigue es de este usuario
        seed_categories(db)
        BUILDERS[state](db)
        db.commit()
    print(f"Listo: estado '{state}'. Entrada: {EMAIL}")


if __name__ == "__main__":
    state = sys.argv[1] if len(sys.argv) > 1 else "worst"
    if state not in BUILDERS:
        sys.exit(f"Estado desconocido. Usa: {', '.join(BUILDERS)}")
    main(state)
