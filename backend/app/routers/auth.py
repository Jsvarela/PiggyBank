from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import mailer
from app.config import settings
from app.db import get_db
from app.deps import COOKIE, get_current_user
from app.models import User
from app.ratelimit import limiter
from app.schemas import Credentials, UserOut
from app.security import SESSION_DAYS, create_token, verify_password
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

PASSWORD = Field(min_length=8, max_length=128)


class EmailIn(BaseModel):
    email: str = Field(max_length=255)


class TokenIn(BaseModel):
    token: str = Field(max_length=2000)


class ResetIn(TokenIn):
    password: str = PASSWORD


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = PASSWORD


class PasswordIn(BaseModel):
    password: str = Field(max_length=128)


def _set_cookie(response: Response, user: User) -> None:
    response.set_cookie(
        COOKIE,
        create_token(user.id, user.token_version),
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore[arg-type]
    )


def _out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, email_verified=user.email_verified_at is not None)


def _require_password(user: User, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=403, detail="La contraseña no es correcta")


@router.post("/register", status_code=201, response_model=UserOut)
@limiter.limit("10/hour")
def register(request: Request, body: Credentials, background: BackgroundTasks, db: Session = Depends(get_db)):
    user = auth_service.register(db, body.email, body.password)
    if settings.email_enabled:
        background.add_task(mailer.send_email, *auth_service.verification_message(user))
    return _out(user)


@router.post("/login", response_model=UserOut)
@limiter.limit("5/minute")
def login(request: Request, response: Response, body: Credentials, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, body.email, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    _set_cookie(response, user)
    return _out(user)


@router.post("/logout", status_code=204)
def logout(response: Response):
    """Cierra la sesión de ESTE dispositivo (borra su cookie)."""
    response.delete_cookie(COOKIE)


@router.post("/logout-all", status_code=204)
def logout_all(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cierra la sesión en TODOS los dispositivos: invalida todo token emitido hasta ahora."""
    auth_service.revoke_sessions(db, user)
    response.delete_cookie(COOKIE)


@router.get("/me", response_model=UserOut)
def me(response: Response, user: User = Depends(get_current_user)):
    _set_cookie(response, user)  # sesión deslizante: cada visita extiende 30 días
    return _out(user)


@router.post("/forgot-password", status_code=204)
@limiter.limit("5/hour")
def forgot_password(request: Request, body: EmailIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    # siempre 204: no revela si el correo está registrado
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user and settings.email_enabled:
        background.add_task(mailer.send_email, *auth_service.reset_message(user))


@router.post("/reset-password", status_code=204)
@limiter.limit("10/hour")
def reset_password(request: Request, body: ResetIn, db: Session = Depends(get_db)):
    auth_service.reset_password(db, body.token, body.password)


@router.post("/verify-email", status_code=204)
@limiter.limit("10/hour")
def verify_email(request: Request, body: TokenIn, db: Session = Depends(get_db)):
    auth_service.verify_email(db, body.token)


@router.post("/send-verification", status_code=204)
@limiter.limit("5/hour")
def send_verification(
    request: Request, background: BackgroundTasks, user: User = Depends(get_current_user)
):
    if user.email_verified_at is None and settings.email_enabled:
        background.add_task(mailer.send_email, *auth_service.verification_message(user))


@router.post("/change-password", status_code=204)
@limiter.limit("10/hour")
def change_password(
    request: Request, response: Response, body: ChangePasswordIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _require_password(user, body.current_password)
    auth_service.set_password(db, user, body.new_password)
    _set_cookie(response, user)  # este dispositivo sigue dentro; los demás quedan cerrados


@router.delete("/account", status_code=204)
@limiter.limit("5/hour")
def delete_account(
    request: Request, response: Response, body: PasswordIn,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    _require_password(user, body.password)
    auth_service.delete_account(db, user)
    response.delete_cookie(COOKIE)
