from datetime import UTC, date, datetime

from app.models import Account, AccountType, Category, CategoryKind, Transaction, TxType
from app.services.balances import account_balances, month_totals, net_worth
from app.timeutil import month_range, today_bogota


def setup_data(db):
    efectivo = Account(name="Efectivo", type=AccountType.cash, initial_balance=100_000)
    banco = Account(name="Bancolombia", type=AccountType.bank, initial_balance=500_000)
    tarjeta = Account(name="Tarjeta", type=AccountType.credit_card, initial_balance=-200_000)
    comida = Category(name="Comida", kind=CategoryKind.expense)
    salario = Category(name="Salario", kind=CategoryKind.income)
    db.add_all([efectivo, banco, tarjeta, comida, salario])
    db.flush()
    return efectivo, banco, tarjeta, comida, salario


def tx(db, type_, amount, d, account, to=None, category=None):
    db.add(
        Transaction(
            type=type_, amount=amount, date=d, account_id=account.id,
            to_account_id=to.id if to else None,
            category_id=category.id if category else None,
        )
    )
    db.flush()


def test_saldo_con_ingresos_gastos_y_transferencias_en_ambas_direcciones(db):
    efectivo, banco, _, comida, salario = setup_data(db)
    d = date(2026, 3, 10)
    tx(db, TxType.income, 1_000_000, d, banco, category=salario)
    tx(db, TxType.expense, 30_000, d, banco, category=comida)
    tx(db, TxType.transfer, 200_000, d, banco, to=efectivo)  # banco -> efectivo
    tx(db, TxType.transfer, 50_000, d, efectivo, to=banco)  # efectivo -> banco
    b = account_balances(db)
    assert b[banco.id] == 500_000 + 1_000_000 - 30_000 - 200_000 + 50_000
    assert b[efectivo.id] == 100_000 + 200_000 - 50_000


def test_transferencia_no_cuenta_en_ingresos_ni_gastos(db):
    efectivo, banco, _, comida, salario = setup_data(db)
    d = date(2026, 3, 10)
    tx(db, TxType.income, 1_000, d, banco, category=salario)
    tx(db, TxType.expense, 400, d, banco, category=comida)
    tx(db, TxType.transfer, 999_999, d, banco, to=efectivo)
    assert month_totals(db, *month_range(d)) == (1_000, 400)


def test_totales_del_mes_ignoran_otros_meses(db):
    _, banco, _, comida, _ = setup_data(db)
    tx(db, TxType.expense, 10, date(2026, 2, 28), banco, category=comida)
    tx(db, TxType.expense, 20, date(2026, 3, 1), banco, category=comida)
    tx(db, TxType.expense, 40, date(2026, 4, 1), banco, category=comida)
    assert month_totals(db, *month_range(date(2026, 3, 15))) == (0, 20)


def test_patrimonio_resta_la_deuda_de_la_tarjeta(db):
    _efectivo, banco, tarjeta, comida, _ = setup_data(db)
    tx(db, TxType.expense, 50_000, date(2026, 3, 1), tarjeta, category=comida)  # compra
    tx(db, TxType.transfer, 100_000, date(2026, 3, 2), banco, to=tarjeta)  # pago
    b = account_balances(db)
    assert b[tarjeta.id] == -200_000 - 50_000 + 100_000
    assert net_worth(b) == 100_000 + 400_000 + b[tarjeta.id]


def test_hoy_se_calcula_en_bogota():
    # 03:00 UTC del 1 de marzo = 22:00 del 28 de febrero en Bogotá
    assert today_bogota(datetime(2026, 3, 1, 3, 0, tzinfo=UTC)) == date(2026, 2, 28)


def test_month_range():
    assert month_range(date(2026, 12, 20)) == (date(2026, 12, 1), date(2027, 1, 1))
