import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.config import settings
from app.ratelimit import limiter

router = APIRouter(tags=["public"])
client_log = logging.getLogger("finanzas.client")


@router.get("/config")
def public_config() -> dict[str, object]:
    """Ajustes que el navegador necesita saber. Nada secreto: solo qué funciones están activas."""
    return {"email_enabled": settings.email_enabled, "analytics_url": settings.analytics_url or None}


class ClientError(BaseModel):
    message: str = Field(max_length=2000)
    stack: str | None = Field(default=None, max_length=8000)
    url: str | None = Field(default=None, max_length=500)


def _one_line(s: str | None) -> str:
    return (s or "").replace("\r", " ").replace("\n", " ")  # evita falsificar líneas del log


@router.post("/client-errors", status_code=204)
@limiter.limit("20/minute")
def client_error(request: Request, body: ClientError):
    """Errores de JavaScript del navegador: quedan en el log del servidor (seguimiento sin servicios externos)."""
    client_log.error(
        "%s | url=%s | ua=%s\n%s",
        _one_line(body.message),
        _one_line(body.url),
        _one_line(request.headers.get("user-agent"))[:200],
        body.stack or "",
    )
