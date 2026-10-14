from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import DomainError
from app.models import User
from app.security import create_purpose_token, decode_purpose_token, hash_password, verify_password
from app.seed import seed_categories
from app.services.backup import wipe_data

RESET_MINUTES = 30
VERIFY_MINUTES = 60 * 24 * 3


class RegistrationClosed(DomainError):
    """Ya existe un usuario: la app es de uso personal (403)."""


def register(db: Session, email: str, password: str) -> User:
    if db.scalar(select(func.count()).select_from(User)):
        raise RegistrationClosed("El registro está cerrado")
    user = User(email=email.lower(), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    # en producción nadie corre el script de seed: sin categorías no se podría registrar ni un gasto
    seed_categories(db)
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower()))
    return user if user and verify_password(password, user.password_hash) else None


def set_password(db: Session, user: User, new_password: str) -> None:
    user.password_hash = hash_password(new_password)
    user.token_version += 1  # cierra todas las sesiones abiertas y deja sin efecto los enlaces viejos
    db.commit()


def revoke_sessions(db: Session, user: User) -> None:
    user.token_version += 1
    db.commit()


def _link(path: str, token: str) -> str:
    return f"{settings.app_url.rstrip('/')}/{path}?token={token}"


def reset_message(user: User) -> tuple[str, str, str]:
    token = create_purpose_token(user.id, "reset", user.token_version, RESET_MINUTES)
    body = (
        "Pediste restablecer tu contraseña de Finanzas.\n\n"
        f"Abre este enlace (vale {RESET_MINUTES} minutos y sirve una sola vez):\n{_link('restablecer', token)}\n\n"
        "Si no fuiste tú, ignora este correo: tu contraseña no cambia."
    )
    return user.email, "Restablece tu contraseña", body


def verification_message(user: User) -> tuple[str, str, str]:
    token = create_purpose_token(user.id, "verify", user.token_version, VERIFY_MINUTES)
    body = (
        "Confirma tu correo para poder recuperar tu contraseña si algún día la olvidas.\n\n"
        f"Abre este enlace:\n{_link('verificar', token)}"
    )
    return user.email, "Confirma tu correo", body


def reset_password(db: Session, token: str, new_password: str) -> None:
    decoded = decode_purpose_token(token, "reset")
    user = db.get(User, decoded[0]) if decoded else None
    if user is None or user.token_version != decoded[1]:
        raise DomainError("El enlace no es válido o ya venció: pide uno nuevo")
    set_password(db, user, new_password)


def verify_email(db: Session, token: str) -> None:
    decoded = decode_purpose_token(token, "verify")
    user = db.get(User, decoded[0]) if decoded else None
    if user is None or user.token_version != decoded[1]:
        raise DomainError("El enlace no es válido o ya venció: pide uno nuevo")
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        db.commit()


def delete_account(db: Session, user: User) -> None:
    """Borra TODOS los datos y el usuario. Después el registro vuelve a estar abierto."""
    wipe_data(db)
    db.execute(delete(User))
    db.commit()
