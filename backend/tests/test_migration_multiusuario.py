"""La migración a multiusuario sobre una base que YA tiene datos: nada se pierde y todo queda de su único dueño."""

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.config import settings

ANTERIOR = "f2e66f436831"  # última revisión de un solo usuario
OWNED = ["accounts", "categories", "transactions", "budgets", "recurring_rules", "savings_goals"]


@pytest.fixture
def base_vieja(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'vieja.db'}"
    monkeypatch.setattr(settings, "database_url", url)  # alembic/env.py lee settings en cada ejecución
    cfg = Config("alembic.ini")
    command.upgrade(cfg, ANTERIOR)
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text("INSERT INTO users (id, email, password_hash, created_at, token_version) VALUES (7, 'yo@example.com', 'x', '2026-01-01', 0)"))
        c.execute(text("INSERT INTO accounts (id, name, type, initial_balance, archived, created_at) VALUES (1, 'Banco', 'bank', 500, 0, '2026-01-01')"))
        c.execute(text("INSERT INTO accounts (id, name, type, initial_balance, archived, created_at) VALUES (2, 'Ahorro', 'savings', 0, 0, '2026-01-01')"))
        c.execute(text("INSERT INTO categories (id, name, kind, archived) VALUES (1, 'Comida', 'expense', 0)"))
        c.execute(text("INSERT INTO transactions (id, type, amount, date, account_id, category_id, tags, created_at) VALUES ('t1', 'expense', 30, '2026-03-01', 1, 1, '[]', '2026-03-01')"))
        c.execute(text("INSERT INTO budgets (id, category_id, is_default, limit_amount, alert_threshold) VALUES (1, 1, 1, 100, 80)"))
        c.execute(text("INSERT INTO recurring_rules (id, type, amount, account_id, category_id, frequency, start_date, next_run_date, active) VALUES (1, 'expense', 10, 1, 1, 'monthly', '2026-01-01', '2026-11-01', 1)"))
        c.execute(text("INSERT INTO savings_goals (id, name, target_amount, account_id, created_at) VALUES (1, 'Meta', 1000, 2, '2026-01-01')"))
    yield eng, cfg
    eng.dispose()


def test_los_datos_existentes_pasan_a_ser_del_unico_usuario_que_queda_como_admin(base_vieja):
    eng, cfg = base_vieja
    command.upgrade(cfg, "head")
    with eng.connect() as c:
        assert c.execute(text("SELECT is_admin FROM users WHERE id = 7")).scalar() in (1, True)
        for tabla in OWNED:
            dueños = {r[0] for r in c.execute(text(f"SELECT user_id FROM {tabla}"))}
            n = c.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
            assert n >= 1 and dueños == {7}, tabla  # nada se perdió y todo es de ese usuario
        assert c.execute(text("SELECT amount FROM transactions WHERE id = 't1'")).scalar() == 30  # datos intactos


def test_user_id_queda_obligatorio_y_la_migracion_se_puede_bajar_y_subir(base_vieja):
    eng, cfg = base_vieja
    command.upgrade(cfg, "head")
    with eng.begin() as c, pytest.raises(Exception, match="(?i)not null|null value"):
        c.execute(text("INSERT INTO accounts (name, type, initial_balance, archived, created_at) VALUES ('x', 'cash', 0, 0, '2026-01-01')"))
    command.downgrade(cfg, ANTERIOR)
    with eng.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM accounts")).scalar() == 2  # al bajar tampoco se pierde nada
    command.upgrade(cfg, "head")
    with eng.connect() as c:
        assert {r[0] for r in c.execute(text("SELECT user_id FROM accounts"))} == {7}


def test_una_base_vacia_tambien_migra(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'nueva.db'}")
    command.upgrade(Config("alembic.ini"), "head")  # instalación nueva: no hay usuario que asignar
