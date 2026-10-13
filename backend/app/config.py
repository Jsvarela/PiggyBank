from pydantic import field_validator, model_validator
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

    @field_validator("database_url")
    @classmethod
    def _driver(cls, v: str) -> str:
        # algunos hostings entregan "postgres://", que SQLAlchemy ya no acepta
        return v.replace("postgres://", "postgresql://", 1) if v.startswith("postgres://") else v

    @model_validator(mode="after")
    def _prod_secret(self):
        if self.cookie_secure and self.secret_key == DEFAULT_SECRET:
            raise ValueError("En producción hay que definir SECRET_KEY (cualquiera puede falsificar sesiones)")
        return self


settings = Settings()
