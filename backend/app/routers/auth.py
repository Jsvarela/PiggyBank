from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import COOKIE, get_current_user
from app.models import User
from app.ratelimit import limiter
from app.schemas import Credentials, UserOut
from app.security import SESSION_DAYS, create_token
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, user_id: int) -> None:
    response.set_cookie(
        COOKIE,
        create_token(user_id),
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )


@router.post("/register", status_code=201, response_model=UserOut)
def register(body: Credentials, db: Session = Depends(get_db)):
    return auth_service.register(db, body.email, body.password)


@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")
def login(request: Request, response: Response, body: Credentials, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    _set_cookie(response, user.id)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response):
    response.delete_cookie(COOKIE)


@router.get("/me", response_model=UserOut)
def me(response: Response, user: User = Depends(get_current_user)):
    _set_cookie(response, user.id)  # sesión deslizante: cada visita extiende 30 días
    return user
