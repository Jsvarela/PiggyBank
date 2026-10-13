from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import User
from app.security import hash_password, verify_password


class RegistrationClosed(DomainError):
    """Ya existe un usuario: la app es de uso personal (403)."""


def register(db: Session, email: str, password: str) -> User:
    if db.scalar(select(func.count()).select_from(User)):
        raise RegistrationClosed("El registro está cerrado")
    user = User(email=email.lower(), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.lower()))
    return user if user and verify_password(password, user.password_hash) else None
