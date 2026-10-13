from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./finanzas.db"
    secret_key: str = "cambia-esto-en-produccion-clave-de-desarrollo"
    frontend_origin: str = "http://localhost:5173"
    cookie_secure: bool = False  # True en producción (HTTPS)
    cookie_samesite: str = "lax"  # "none" si frontend y API están en dominios distintos


settings = Settings()
