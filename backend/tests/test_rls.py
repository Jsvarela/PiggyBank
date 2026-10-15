"""RLS en Postgres: la base de datos aísla por sí sola, aunque la app olvidara filtrar."""

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app import rls
from app.tenancy import Owned, bind_user

ROL = "rls_test"


def test_las_tablas_de_rls_son_las_de_los_modelos_con_dueno():
    assert set(rls.TABLES) == {c.__table__.name for c in Owned.__subclasses__()}  # un modelo nuevo sin política quedaría abierto


@pytest.fixture
def pg(engine):
    if engine.dialect.name != "postgresql":
        pytest.skip("RLS solo existe en Postgres (TEST_DATABASE_URL)")
    with engine.begin() as c:
        for i in (1, 2):
            c.exec_driver_sql(f"INSERT INTO users (id, email, password_hash, created_at, token_version) VALUES ({i}, 'u{i}@x.co', 'x', now(), 0)")
            c.exec_driver_sql(f"INSERT INTO accounts (name, type, initial_balance, archived, created_at, user_id) VALUES ('de {i}', 'cash', 0, false, now(), {i})")
        rls.enable(c)
        c.exec_driver_sql(f"CREATE ROLE {ROL} NOBYPASSRLS")  # como el rol restringido de producción
        c.exec_driver_sql(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROL}")
        c.exec_driver_sql(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO {ROL}")
    yield engine
    engine.dispose()  # las conexiones devueltas al pool conservan SET ROLE: se descartan para limpiar como dueño
    with engine.begin() as c:
        c.exec_driver_sql(f"DROP OWNED BY {ROL}")
        c.exec_driver_sql(f"DROP ROLE {ROL}")


def como_app(pg, user_id):
    """Conexión con el rol restringido y, si se pide, el usuario fijado igual que lo hace la app."""
    conn = pg.connect()
    conn.exec_driver_sql(f"SET ROLE {ROL}")
    if user_id is not None:
        conn.exec_driver_sql("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
    return conn


def nombres(conn):
    return [r[0] for r in conn.exec_driver_sql("SELECT name FROM accounts ORDER BY id")]


def test_cada_usuario_ve_solo_lo_suyo(pg):
    for uid in (1, 2):
        with como_app(pg, uid) as c:
            assert nombres(c) == [f"de {uid}"]


def test_sin_usuario_fijado_no_se_ve_nada(pg):
    with como_app(pg, None) as c:
        assert nombres(c) == []


def test_no_se_puede_escribir_ni_borrar_lo_de_otro(pg):
    with como_app(pg, 1) as c, pytest.raises(DBAPIError):  # WITH CHECK: user_id ajeno
        c.exec_driver_sql("INSERT INTO accounts (name, type, initial_balance, archived, created_at, user_id) VALUES ('x', 'cash', 0, false, now(), 2)")
    with como_app(pg, 1) as c:
        assert c.exec_driver_sql("UPDATE accounts SET name = 'robada' WHERE user_id = 2").rowcount == 0
        assert c.exec_driver_sql("DELETE FROM accounts WHERE user_id = 2").rowcount == 0


def test_bind_user_fija_el_usuario_en_cada_transaccion(pg):
    with pg.connect() as conn:
        conn.exec_driver_sql(f"SET ROLE {ROL}")
        conn.commit()  # sin transacción abierta: así la sesión hace commit de verdad y empieza otra
        with Session(bind=conn) as s:
            s.execute(sa.text("SELECT 1"))  # la transacción ya empezó antes de conocer al usuario (como al leer la sesión)
            bind_user(s, 2)
            assert s.scalar(sa.text("SELECT current_setting('app.user_id', true)")) == "2"
            s.commit()
            assert s.scalar(sa.text("SELECT current_setting('app.user_id', true)")) == "2"  # transacción nueva: after_begin
            assert [r[0] for r in s.execute(sa.text("SELECT name FROM accounts"))] == ["de 2"]
