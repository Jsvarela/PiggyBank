import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.errors import Conflict, DomainError, NotFound
from app.models import Invite, User
from app.security import create_purpose_token, decode_purpose_token, hash_password, verify_password
from app.seed import seed_categories
from app.services.backup import wipe_data
from app.tenancy import bind_user

RESET_MINUTES = 30
VERIFY_MINUTES = 60 * 24 * 3


INVITE_DAYS = 7


class RegistrationClosed(DomainError):
    """Falta una invitación válida (403)."""


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().encode()).hexdigest()


def _aware(d: datetime) -> datetime:
    return d if d.tzinfo else d.replace(tzinfo=UTC)  # SQLite devuelve fechas sin zona; siempre son UTC


def create_invite(db: Session, admin: User) -> tuple[Invite, str]:
    """Crea una invitación de un solo uso. El código en claro solo existe aquí y en la respuesta."""
    code = secrets.token_urlsafe(12)
    invite = Invite(
        code_hash=_hash_code(code), created_by=admin.id, expires_at=datetime.now(UTC) + timedelta(days=INVITE_DAYS)
    )
    db.add(invite)
    db.commit()
    return invite, code


def invite_status(invite: Invite) -> str:
    if invite.used_at is not None:
        return "usada"
    return "vencida" if _aware(invite.expires_at) <= datetime.now(UTC) else "pendiente"


def revoke_invite(db: Session, invite_id: int) -> None:
    invite = db.get(Invite, invite_id)
    if invite is None or invite.used_at is not None:
        raise NotFound("La invitación no existe o ya se usó")
    db.delete(invite)
    db.commit()


def register(db: Session, email: str, password: str, invite_code: str | None = None) -> User:
    """El primer usuario se registra solo y queda como administrador; los demás necesitan una invitación."""
    first = not db.scalar(select(func.count()).select_from(User))
    invite = None
    if not first:
        invite = db.scalar(select(Invite).where(Invite.code_hash == _hash_code(invite_code or "")))
        if invite is None or invite_status(invite) != "pendiente":
            raise RegistrationClosed("La invitación no es válida, ya se usó o venció")
    if db.scalar(select(User.id).where(User.email == email.lower())):
        raise Conflict("Ese correo ya tiene una cuenta")  # antes de gastar la invitación
    user = User(email=email.lower(), password_hash=hash_password(password), is_admin=first)
    db.add(user)
    db.flush()
    if invite is not None:
        # atómico: si dos personas usan el mismo código a la vez, solo una lo consigue
        used = db.execute(
            update(Invite).where(Invite.id == invite.id, Invite.used_at.is_(None)).values(used_at=datetime.now(UTC), used_by=user.id)
        )
        if used.rowcount != 1:
            db.rollback()
            raise RegistrationClosed("La invitación no es válida, ya se usó o venció")
    db.commit()
    # en producción nadie corre el script de seed: sin categorías no se podría registrar ni un gasto
    bind_user(db, user.id)  # las categorías por defecto son de esta persona
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
    """Borra los datos de ESTA persona (el filtro de tenancy los limita a ella) y su usuario."""
    if user.is_admin and db.scalar(select(func.count()).select_from(User).where(User.id != user.id)):
        raise Conflict("Eres el administrador y hay otras personas usando la app: no puedes borrar tu cuenta todavía")
    wipe_data(db)
    db.execute(delete(Invite).where(Invite.created_by == user.id))  # solo existen si era el único usuario
    db.execute(update(Invite).where(Invite.used_by == user.id).values(used_by=None))  # queda el registro, sin dueño
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
