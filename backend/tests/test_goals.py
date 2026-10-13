from datetime import date

import pytest

from app.errors import DomainError
from app.models import Account, AccountType, SavingsGoal, Transaction, TxType
from app.services.balances import account_balances, month_totals
from app.services.goals import contribute, goal_progress, monthly_suggestion
from app.timeutil import month_range

HOY = date(2026, 10, 13)


def setup(db, with_account=True, **kw):
    banco = Account(name="Banco", type=AccountType.bank, initial_balance=1_000_000)
    ahorro = Account(name="Ahorro", type=AccountType.savings, initial_balance=0)
    db.add_all([banco, ahorro])
    db.flush()
    goal = SavingsGoal(name="Viaje", target_amount=kw.pop("target", 1_000_000),
                       account_id=ahorro.id if with_account else None, **kw)
    db.add(goal)
    db.flush()
    return banco, ahorro, goal


def test_aportar_crea_transferencia_y_mueve_saldos(db):
    banco, ahorro, goal = setup(db)
    contribute(db, goal, banco.id, 250_000, HOY)
    (t,) = db.query(Transaction).all()
    assert (t.type, t.account_id, t.to_account_id, t.goal_id, t.category_id) == (
        TxType.transfer, banco.id, ahorro.id, goal.id, None)
    b = account_balances(db)
    assert (b[banco.id], b[ahorro.id]) == (750_000, 250_000)
    assert month_totals(db, *month_range(HOY)) == (0, 0)  # una transferencia no es gasto


def test_progreso_suma_los_aportes(db):
    banco, _, goal = setup(db, target=1_000_000)
    contribute(db, goal, banco.id, 250_000, HOY)
    contribute(db, goal, banco.id, 100_000, HOY)
    p = goal_progress(db, goal, HOY)
    assert (p.saved, p.remaining, p.percent, p.reached) == (350_000, 650_000, 35, False)


def test_meta_cumplida(db):
    banco, _, goal = setup(db, target=100_000)
    contribute(db, goal, banco.id, 150_000, HOY)
    p = goal_progress(db, goal, HOY)
    assert (p.reached, p.remaining, p.monthly_suggested) == (True, 0, 0)
    assert p.percent == 150


def test_aportar_exige_cuenta_de_ahorro_en_la_meta(db):
    banco, _, goal = setup(db, with_account=False)
    with pytest.raises(DomainError):
        contribute(db, goal, banco.id, 1_000, HOY)
    assert db.query(Transaction).count() == 0


def test_no_se_aporta_desde_la_cuenta_de_la_meta(db):
    _, ahorro, goal = setup(db)
    with pytest.raises(DomainError):
        contribute(db, goal, ahorro.id, 1_000, HOY)


def test_monto_suma_mensual_sugerida_redondea_hacia_arriba():
    g = SavingsGoal(name="x", target_amount=1_000_000, deadline=date(2027, 1, 13))
    assert monthly_suggestion(g, saved=0, today=HOY) == 333_334  # 3 meses
    assert monthly_suggestion(g, saved=400_000, today=HOY) == 200_000


def test_sugerida_sin_fecha_limite_o_con_fecha_vencida_o_mismo_mes():
    sin = SavingsGoal(name="x", target_amount=1_000, deadline=None)
    assert monthly_suggestion(sin, 0, HOY) is None
    vencida = SavingsGoal(name="x", target_amount=1_000, deadline=date(2026, 9, 1))
    assert monthly_suggestion(vencida, 400, HOY) == 600  # todo lo que falta, ya
    este_mes = SavingsGoal(name="x", target_amount=1_000, deadline=date(2026, 10, 31))
    assert monthly_suggestion(este_mes, 0, HOY) == 1_000
