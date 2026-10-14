import os

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET = "cambia-esto-en-produccion-clave-de-desarrollo"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./finanzas.db"
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

    @field_validator("database_url")
    @classmethod
    def _driver(cls, v: str) -> str:
        # "postgres://" ya no lo acepta SQLAlchemy, y "postgresql+psycopg://" pide un driver (psycopg 3)
        # que no usamos: ambos se llevan a "postgresql://", que usa psycopg2 (el instalado).
        for prefix in ("postgres://", "postgresql+psycopg://"):
            if v.startswith(prefix):
                return "postgresql://" + v[len(prefix) :]
        return v

    @model_validator(mode="after")
    def _prod_secret(self):
        if self.cookie_secure and self.secret_key == DEFAULT_SECRET:
            raise ValueError("En producción hay que definir SECRET_KEY (cualquiera puede falsificar sesiones)")
        return self


settings = Settings()
