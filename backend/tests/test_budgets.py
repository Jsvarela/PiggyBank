from datetime import date

from app.models import (
    Account,
    AccountType,
    Budget,
    Category,
    CategoryKind,
    Transaction,
    TxType,
)
from app.services.budgets import budget_status, monthly_report

HOY = date(2026, 10, 12)


def setup(db):
    cuenta = Account(name="Banco", type=AccountType.bank, initial_balance=0)
    otra = Account(name="Efectivo", type=AccountType.cash, initial_balance=0)
    comida = Category(name="Comida", kind=CategoryKind.expense)
    vivienda = Category(name="Vivienda", kind=CategoryKind.expense)
    salario = Category(name="Salario", kind=CategoryKind.income)
    db.add_all([cuenta, otra, comida, vivienda, salario])
    db.flush()
    arriendo = Category(name="Arriendo", kind=CategoryKind.expense, parent_id=vivienda.id)
    db.add(arriendo)
    db.flush()
    return cuenta, otra, comida, vivienda, arriendo, salario


def gasto(db, cuenta, cat, monto, d):
    db.add(Transaction(type=TxType.expense, amount=monto, date=d, account_id=cuenta.id, category_id=cat.id))
    db.flush()


def budget(db, cat, limit, month=None, threshold=80):
    db.add(
        Budget(category_id=cat.id, month=month, is_default=month is None, limit_amount=limit, alert_threshold=threshold)
    )
    db.flush()


def one(db, month="2026-10"):
    (item,) = budget_status(db, month, HOY)
    return item


def test_presupuesto_por_defecto_aplica_a_cualquier_mes_y_el_del_mes_gana(db):
    _, _, comida, *_ = setup(db)
    budget(db, comida, 100_000)
    assert one(db, "2026-10").limit == 100_000
    assert one(db, "2027-01").limit == 100_000
    budget(db, comida, 150_000, month="2026-10")
    assert one(db, "2026-10").limit == 150_000
    assert one(db, "2026-10").is_default is False
    assert one(db, "2026-11").limit == 100_000


def test_solo_cuentan_gastos_del_mes(db):
    cuenta, otra, comida, _, _, salario = setup(db)
    budget(db, comida, 100_000)
    gasto(db, cuenta, comida, 10_000, date(2026, 10, 1))
    gasto(db, cuenta, comida, 5_000, date(2026, 10, 31))
    gasto(db, cuenta, comida, 999, date(2026, 9, 30))  # mes anterior
    gasto(db, cuenta, comida, 999, date(2026, 11, 1))  # mes siguiente
    db.add(Transaction(type=TxType.transfer, amount=50_000, date=HOY, account_id=cuenta.id, to_account_id=otra.id))
    db.add(Transaction(type=TxType.income, amount=70_000, date=HOY, account_id=cuenta.id, category_id=salario.id))
    db.flush()
    assert one(db).spent == 15_000


def test_presupuesto_del_padre_suma_subcategorias(db):
    cuenta, _, _, vivienda, arriendo, _ = setup(db)
    budget(db, vivienda, 1_000_000)
    gasto(db, cuenta, vivienda, 100_000, HOY)
    gasto(db, cuenta, arriendo, 400_000, HOY)
    assert one(db).spent == 500_000


def test_presupuesto_de_subcategoria_solo_cuenta_la_suya(db):
    cuenta, _, _, vivienda, arriendo, _ = setup(db)
    budget(db, arriendo, 1_000_000)
    gasto(db, cuenta, vivienda, 100_000, HOY)
    gasto(db, cuenta, arriendo, 400_000, HOY)
    assert one(db).spent == 400_000


def test_alertas_por_umbral_y_exceso(db):
    cuenta, _, comida, *_ = setup(db)
    budget(db, comida, 1_000)
    casos = [(799, "ok"), (800, "warning"), (1_000, "warning"), (1_001, "exceeded")]
    for gastado, esperado in casos:
        db.query(Transaction).delete()
        gasto(db, cuenta, comida, gastado, HOY)
        assert one(db).alert == esperado, gastado


def test_umbral_personalizado(db):
    cuenta, _, comida, *_ = setup(db)
    budget(db, comida, 1_000, threshold=50)
    gasto(db, cuenta, comida, 500, HOY)
    assert one(db).alert == "warning"


def test_porcentaje_restante_y_dias(db):
    cuenta, _, comida, *_ = setup(db)
    budget(db, comida, 200_000)
    gasto(db, cuenta, comida, 50_000, HOY)
    item = one(db)
    assert (item.percent, item.remaining) == (25, 150_000)
    assert item.days_left == 19  # del 12 al 31 de octubre
    assert one(db, "2026-09").days_left == 0  # mes pasado
    assert one(db, "2026-11").days_left == 30  # mes futuro: el mes completo


def test_sin_presupuesto_no_aparece(db):
    setup(db)
    assert budget_status(db, "2026-10", HOY) == []


def test_resumen_mensual_agrupa_en_categoria_principal_y_compara(db):
    cuenta, _, comida, vivienda, arriendo, salario = setup(db)
    gasto(db, cuenta, comida, 30_000, date(2026, 10, 3))
    gasto(db, cuenta, arriendo, 400_000, date(2026, 10, 5))
    gasto(db, cuenta, vivienda, 100_000, date(2026, 10, 6))
    gasto(db, cuenta, comida, 20_000, date(2026, 9, 10))
    db.add(Transaction(type=TxType.income, amount=1_000_000, date=date(2026, 10, 1), account_id=cuenta.id, category_id=salario.id))
    db.flush()
    r = monthly_report(db, "2026-10")
    assert (r.income, r.expense) == (1_000_000, 530_000)
    assert (r.previous_income, r.previous_expense) == (0, 20_000)
    by_name = {c.name: c for c in r.categories}
    assert by_name["Vivienda"].amount == 500_000  # padre + hija
    assert by_name["Comida"].previous == 20_000 and by_name["Comida"].diff == 10_000
    assert r.categories[0].name == "Vivienda"  # ordenado de mayor a menor
