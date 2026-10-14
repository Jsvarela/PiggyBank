"""Prueba del mecanismo de aislamiento en sí (no de las rutas): el filtro automático debe cubrir
consultas normales, agregados, borrados/actualizaciones masivas y búsquedas por id, y fallar cerrado."""

from datetime import date

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import Account, AccountType, Category, CategoryKind, Transaction, TxType, User
from app.tenancy import TenantError


@pytest.fixture
def dos(engine):
    """Dos usuarios con datos propios y una sesión por cada uno."""
    with Session(engine) as admin:
        a, b = User(email="a@example.com", password_hash="x"), User(email="b@example.com", password_hash="x")
        admin.add_all([a, b])
        admin.commit()
        ids = (a.id, b.id)

    def sesion(user_id):
        s = Session(engine)
        s.info["user_id"] = user_id
        return s

    sa, sb = sesion(ids[0]), sesion(ids[1])
    for s, base in ((sa, 1_000), (sb, 5)):
        cuenta = Account(name=f"cuenta {base}", type=AccountType.bank, initial_balance=0)
        cat = Category(name=f"cat {base}", kind=CategoryKind.expense)
        s.add_all([cuenta, cat])
        s.flush()
        for i in range(3):
            s.add(Transaction(type=TxType.expense, amount=base, date=date(2026, 3, 1 + i), account_id=cuenta.id, category_id=cat.id))
        s.commit()
    yield sa, sb
    sa.close()
    sb.close()


def test_consulta_normal_solo_ve_lo_propio(dos):
    sa, sb = dos
    assert [c.name for c in sa.scalars(select(Account))] == ["cuenta 1000"]
    assert [c.name for c in sb.scalars(select(Account))] == ["cuenta 5"]
    assert sa.scalar(select(func.count()).select_from(Transaction)) == 3


def test_agregados_solo_suman_lo_propio(dos):
    sa, sb = dos
    assert sa.scalar(select(func.sum(Transaction.amount))) == 3_000
    assert sb.scalar(select(func.sum(Transaction.amount))) == 15
    por_cuenta = sb.execute(select(Transaction.account_id, func.sum(Transaction.amount)).group_by(Transaction.account_id)).all()
    assert [total for _, total in por_cuenta] == [15]


def test_buscar_por_id_ajeno_devuelve_nada(dos):
    sa, sb = dos
    ajena = sa.scalars(select(Account)).one()
    assert sb.get(Account, ajena.id) is None
    assert sb.scalar(select(Account).where(Account.id == ajena.id)) is None


def test_borrado_masivo_solo_borra_lo_propio(dos, engine):
    sa, sb = dos
    sb.execute(delete(Transaction))
    sb.commit()
    assert sb.scalar(select(func.count()).select_from(Transaction)) == 0
    assert sa.scalar(select(func.count()).select_from(Transaction)) == 3  # lo de A sigue ahí


def test_actualizacion_masiva_solo_toca_lo_propio(dos):
    sa, sb = dos
    sb.execute(update(Account).values(name="renombrada"))
    sb.commit()
    assert [c.name for c in sb.scalars(select(Account))] == ["renombrada"]
    assert [c.name for c in sa.scalars(select(Account))] == ["cuenta 1000"]


def test_join_tambien_queda_filtrado(dos):
    _sa, sb = dos
    filas = sb.execute(select(Transaction.amount, Account.name).join(Account, Account.id == Transaction.account_id)).all()
    assert {(m, n) for m, n in filas} == {(5, "cuenta 5")}


def test_formas_raras_nunca_filtran_datos_ajenos(dos):
    """Subconsultas y alias: o salen filtradas o se rechazan, pero jamás devuelven filas de otra persona."""
    from sqlalchemy.orm import aliased

    _, sb = dos
    sub = select(Transaction.id).subquery()
    consultas = [
        select(func.count()).select_from(sub),
        select(func.count()).where(Transaction.id.in_(select(Transaction.id))),
        select(func.count()).select_from(aliased(Transaction)),
        select(Account.name).where(Account.id.in_(select(Transaction.account_id))),
    ]
    for q in consultas:
        try:
            resultado = sb.execute(q).all()
        except TenantError:
            continue  # rechazada: es válido (cerrado por defecto)
        assert resultado in ([(3,)], [("cuenta 5",)]), f"fuga con {q}: {resultado}"


def test_sin_usuario_en_la_sesion_falla_cerrado(engine):
    with Session(engine) as s:  # sin user_id
        with pytest.raises(TenantError):
            s.scalars(select(Account)).all()
        with pytest.raises(TenantError):
            s.execute(delete(Transaction))
        s.add(Account(name="x", type=AccountType.cash, initial_balance=0))
        with pytest.raises(TenantError):
            s.flush()


def test_los_usuarios_no_tienen_dueno(engine):
    with Session(engine) as s:  # login y registro consultan usuarios sin tener a nadie "dentro"
        s.add(User(email="z@example.com", password_hash="x"))
        s.commit()
        assert s.scalar(select(func.count()).select_from(User)) >= 1


def test_objeto_nuevo_recibe_el_dueno_de_la_sesion(dos):
    sa, _ = dos
    nueva = Account(name="nueva", type=AccountType.cash, initial_balance=0)
    sa.add(nueva)
    sa.commit()
    dueno_a = sa.info["user_id"]
    assert nueva.user_id == dueno_a
