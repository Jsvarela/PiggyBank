from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import decode_token

COOKIE = "session"


def get_current_user(
    session: str | None = Cookie(default=None), db: Session = Depends(get_db)
) -> User:
    user_id = decode_token(session) if session else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="No autenticado")
    return user
