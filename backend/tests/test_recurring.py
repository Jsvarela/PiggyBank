from datetime import date

from sqlalchemy import select

from app.models import (
    Account,
    AccountType,
    Category,
    CategoryKind,
    Frequency,
    RecurringRule,
    Transaction,
    TxType,
)
from app.services.recurring import next_occurrence, sync_recurring, upcoming

HOY = date(2026, 10, 13)


def occurrences(start, freq, n):
    out, d = [start], start
    for _ in range(n - 1):
        d = next_occurrence(start, freq, d)
        out.append(d)
    return out


def test_mensual_dia_31_vuelve_al_31_despues_de_febrero():
    assert occurrences(date(2027, 1, 31), Frequency.monthly, 5) == [
        date(2027, 1, 31), date(2027, 2, 28), date(2027, 3, 31), date(2027, 4, 30), date(2027, 5, 31),
    ]


def test_mensual_febrero_bisiesto_y_cambio_de_anio():
    assert next_occurrence(date(2028, 1, 31), Frequency.monthly, date(2028, 1, 31)) == date(2028, 2, 29)
    assert next_occurrence(date(2026, 12, 15), Frequency.monthly, date(2026, 12, 15)) == date(2027, 1, 15)


def test_anual_29_de_febrero():
    assert occurrences(date(2028, 2, 29), Frequency.yearly, 5) == [
        date(2028, 2, 29), date(2029, 2, 28), date(2030, 2, 28), date(2031, 2, 28), date(2032, 2, 29),
    ]


def test_diaria_semanal_y_quincenal():
    d = date(2026, 12, 30)
    assert next_occurrence(d, Frequency.daily, d) == date(2026, 12, 31)
    assert next_occurrence(d, Frequency.weekly, d) == date(2027, 1, 6)
    assert next_occurrence(d, Frequency.biweekly, d) == date(2027, 1, 13)


def setup(db):
    banco = Account(name="Banco", type=AccountType.bank, initial_balance=0)
    ahorro = Account(name="Ahorro", type=AccountType.savings, initial_balance=0)
    arriendo = Category(name="Vivienda", kind=CategoryKind.expense)
    salario = Category(name="Salario", kind=CategoryKind.income)
    db.add_all([banco, ahorro, arriendo, salario])
    db.flush()
    return banco, ahorro, arriendo, salario


def rule(db, banco, cat, start, **kw):
    r = RecurringRule(
        type=kw.pop("type", TxType.expense), amount=kw.pop("amount", 100), account_id=banco.id,
        category_id=cat.id if cat else None, description=kw.pop("description", "Arriendo"),
        frequency=kw.pop("frequency", Frequency.monthly), start_date=start,
        next_run_date=start, active=kw.pop("active", True), **kw,
    )
    db.add(r)
    db.flush()
    return r


def generated(db, r):
    return db.scalars(
        select(Transaction).where(Transaction.recurring_rule_id == r.id).order_by(Transaction.date)
    ).all()


def test_varias_ejecuciones_atrasadas_se_ponen_al_dia(db):
    banco, _, vivienda, _ = setup(db)
    r = rule(db, banco, vivienda, date(2026, 7, 15))
    assert sync_recurring(db, HOY) == 3
    assert [t.date for t in generated(db, r)] == [date(2026, 7, 15), date(2026, 8, 15), date(2026, 9, 15)]
    assert r.next_run_date == date(2026, 10, 15)


def test_sync_es_idempotente(db):
    banco, _, vivienda, _ = setup(db)
    r = rule(db, banco, vivienda, date(2026, 7, 15))
    sync_recurring(db, HOY)
    assert sync_recurring(db, HOY) == 0
    assert sync_recurring(db, HOY) == 0
    assert len(generated(db, r)) == 3


def test_no_duplica_si_el_movimiento_ya_existia(db):
    # simula una ejecución anterior que creó el movimiento pero no alcanzó a avanzar la regla
    banco, _, vivienda, _ = setup(db)
    r = rule(db, banco, vivienda, date(2026, 9, 15))
    db.add(Transaction(type=TxType.expense, amount=100, date=date(2026, 9, 15), account_id=banco.id,
                       category_id=vivienda.id, recurring_rule_id=r.id))
    db.flush()
    assert sync_recurring(db, HOY) == 0
    assert len(generated(db, r)) == 1
    assert r.next_run_date == date(2026, 10, 15)


def test_respeta_end_date(db):
    banco, _, vivienda, _ = setup(db)
    r = rule(db, banco, vivienda, date(2026, 7, 15), end_date=date(2026, 8, 20))
    assert sync_recurring(db, HOY) == 2
    assert [t.date for t in generated(db, r)] == [date(2026, 7, 15), date(2026, 8, 15)]
    assert sync_recurring(db, date(2027, 6, 1)) == 0


def test_ultimo_dia_exacto_del_end_date_se_incluye(db):
    banco, _, vivienda, _ = setup(db)
    r = rule(db, banco, vivienda, date(2026, 7, 15), end_date=date(2026, 8, 15))
    assert sync_recurring(db, HOY) == 2
    assert generated(db, r)[-1].date == date(2026, 8, 15)


def test_reglas_inactivas_o_futuras_no_generan(db):
    banco, _, vivienda, _ = setup(db)
    off = rule(db, banco, vivienda, date(2026, 7, 15), active=False)
    futura = rule(db, banco, vivienda, date(2026, 10, 14))
    assert sync_recurring(db, HOY) == 0
    assert generated(db, off) == [] and generated(db, futura) == []


def test_hoy_mismo_se_ejecuta_y_copia_los_campos_de_la_plantilla(db):
    banco, _, _, salario = setup(db)
    r = rule(db, banco, salario, HOY, type=TxType.income, amount=2_000_000, description="Nómina")
    assert sync_recurring(db, HOY) == 1
    (t,) = generated(db, r)
    assert (t.type, t.amount, t.date, t.account_id, t.category_id, t.description) == (
        TxType.income, 2_000_000, HOY, banco.id, salario.id, "Nómina")


def test_regla_de_transferencia(db):
    banco, ahorro, _, _ = setup(db)
    r = rule(db, banco, None, HOY, type=TxType.transfer, amount=50_000, to_account_id=ahorro.id)
    assert sync_recurring(db, HOY) == 1
    (t,) = generated(db, r)
    assert (t.type, t.to_account_id, t.category_id) == (TxType.transfer, ahorro.id, None)


def test_proximos_pagos_30_dias(db):
    banco, _, vivienda, _ = setup(db)
    mensual = rule(db, banco, vivienda, date(2026, 10, 20))
    semanal = rule(db, banco, vivienda, date(2026, 10, 14), frequency=Frequency.weekly, description="Semanal")
    rule(db, banco, vivienda, date(2026, 10, 15), active=False)
    rule(db, banco, vivienda, date(2026, 10, 15), end_date=date(2026, 10, 14))  # ya terminada
    items = upcoming(db, HOY, 30)
    fechas = [(i.rule_id, i.date) for i in items]
    assert (mensual.id, date(2026, 10, 20)) in fechas
    assert (mensual.id, date(2026, 11, 20)) not in fechas  # fuera de la ventana (hasta el 12/nov)
    assert [d for r, d in fechas if r == semanal.id] == [
        date(2026, 10, 14), date(2026, 10, 21), date(2026, 10, 28), date(2026, 11, 4), date(2026, 11, 11),
    ]
    assert len({i.rule_id for i in items}) == 2
    assert fechas == sorted(fechas, key=lambda x: x[1])  # ordenados por fecha
