import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "cambia-esto-en-produccion-clave-de-desarrollo"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./finanzas.db"
    # Solo para Alembic (crear/alterar tablas). Con RLS, DATABASE_URL debe ser un rol SIN BYPASSRLS y las
    # migraciones corren con el dueño. Vacía = Alembic usa DATABASE_URL.
    migration_database_url: str = ""
    secret_key: str = DEFAULT_SECRET
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False  # True en producción (HTTPS)
    cookie_samesite: str = "lax"  # "none" solo si frontend y API estuvieran en dominios distintos
    static_dir: str = ""  # carpeta del frontend compilado; vacía en desarrollo (corre Vite aparte)

    # Correo (recuperar contraseña y verificar correo). Sin SMTP_HOST esas funciones quedan apagadas.
    smtp_host: str = ""
    smtp_port: int = 587  # STARTTLS
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    # Base de los enlaces de los correos. En Render se toma sola de RENDER_EXTERNAL_URL.
    app_url: str = Field(default_factory=lambda: os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5173"))

    # Analítica opcional (GoatCounter, sin cookies): "https://TU-CODIGO.goatcounter.com/count". Vacía = apagada.
    analytics_url: str = ""

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_host)

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def _driver(cls, v: str) -> str:
        # Cualquier URL de Postgres se lleva al driver que sí instalamos (psycopg2). Hace falta nombrarlo:
        # SQLAlchemy 2.1 cambió el driver por defecto de "postgresql://" a psycopg 3, y "postgres://"
        # (estilo antiguo de algunos hostings) ya no se acepta.
        for prefix in ("postgres://", "postgresql://", "postgresql+psycopg://"):
            if v.startswith(prefix):
                return "postgresql+psycopg2://" + v[len(prefix) :]
        return v

    @model_validator(mode="after")
    def _prod_secret(self):
        if self.cookie_secure and self.secret_key == DEFAULT_SECRET:
            raise ValueError("En producción hay que definir SECRET_KEY (cualquiera puede falsificar sesiones)")
        return self


settings = Settings()
