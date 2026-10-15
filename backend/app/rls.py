"""Row Level Security (Postgres): la base de datos misma impide ver o tocar filas de otro usuario.

Segunda barrera tras el filtro de app/tenancy.py. Cada política compara `user_id` con `app.user_id`, que la app
fija en cada transacción (tenancy.bind_user). Sin usuario fijado, la política no deja pasar ninguna fila.

OJO: RLS no se aplica a superusuarios ni a roles con BYPASSRLS (el rol por defecto de Neon lo tiene). La app
debe conectarse con un rol sin ese atributo; ver DEPLOY.md. `warn_if_bypassed` avisa en el log si no es así.
"""

import logging

from sqlalchemy import Connection, Engine

log = logging.getLogger("finanzas.rls")

# Debe coincidir con los modelos `Owned` (lo comprueba tests/test_rls.py).
TABLES = ("accounts", "categories", "transactions", "budgets", "recurring_rules", "savings_goals", "loans")
_USER = "NULLIF(current_setting('app.user_id', true), '')::integer"


def enable(conn: Connection) -> None:
    for t in TABLES:
        conn.exec_driver_sql(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        conn.exec_driver_sql(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")  # también aplica al dueño de la tabla
        conn.exec_driver_sql(f"DROP POLICY IF EXISTS tenant ON {t}")
        conn.exec_driver_sql(f"CREATE POLICY tenant ON {t} USING (user_id = {_USER}) WITH CHECK (user_id = {_USER})")


def disable(conn: Connection) -> None:
    for t in TABLES:
        conn.exec_driver_sql(f"DROP POLICY IF EXISTS tenant ON {t}")
        conn.exec_driver_sql(f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY")
        conn.exec_driver_sql(f"ALTER TABLE {t} DISABLE ROW LEVEL SECURITY")


def warn_if_bypassed(engine: Engine) -> None:
    """Avisa (sin frenar el arranque) si el rol de la app se salta RLS, porque entonces las políticas no sirven."""
    if engine.dialect.name != "postgresql":
        return
    try:
        with engine.connect() as c:
            bypass = c.exec_driver_sql("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user").scalar()
    except Exception:
        log.exception("No se pudo comprobar si el rol de la base se salta RLS")
        return
    if bypass:
        log.warning("RLS NO está protegiendo: el rol de DATABASE_URL es superusuario o tiene BYPASSRLS. Usa un rol restringido (DEPLOY.md).")
