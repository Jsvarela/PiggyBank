from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token

COOKIE = "session"


def get_current_user(
    session: str | None = Cookie(default=None), db: Session = Depends(get_db)
) -> User:
    decoded = decode_token(session) if session else None
    user = db.get(User, decoded[0]) if decoded else None
    if user is None or user.token_version != decoded[1]:
        raise HTTPException(status_code=401, detail="No autenticado")
    # Desde aquí, TODA consulta de esta petición queda limitada a los datos de este usuario (app/tenancy.py).
    # `db` es la misma sesión que recibe la ruta: FastAPI comparte la dependencia get_db dentro de una petición.
    db.info["user_id"] = user.id
    return user


def get_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Solo el administrador puede hacer esto")
    return user
