from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.errors import Conflict, DomainError, NotFound
from app.ratelimit import limiter
from app.routers import (
    auth,
    budgets,
    catalog,
    export,
    goals,
    loans,
    public,
    recurring,
    statement,
    transactions,
)
from app.services.auth import RegistrationClosed
from app.spa import mount_frontend

app = FastAPI(title="Finanzas")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)  # aplica el tope general por IP a toda la API

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATUS = {NotFound: 404, Conflict: 409, RegistrationClosed: 403, DomainError: 422}


@app.exception_handler(DomainError)
def domain_error(_: Request, exc: DomainError):
    return JSONResponse({"detail": str(exc)}, status_code=_STATUS[type(exc)])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


for r in (
    auth.router, catalog.router, transactions.router, budgets.router, recurring.router, goals.router, loans.router,
    export.router, statement.router, public.router,
):
    app.include_router(r, prefix="/api")

# debe ir al final: la ruta comodín del frontend no puede tapar a la API
if settings.static_dir:
    mount_frontend(app, Path(settings.static_dir))
