from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings

SESSION_DAYS = 30
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except VerifyMismatchError:
        return False


def _encode(claims: dict, expires: timedelta) -> str:
    return jwt.encode({**claims, "exp": datetime.now(UTC) + expires}, settings.secret_key, algorithm="HS256")


def _decode(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


# `v` es la versión de sesión del usuario: cambiarla (nueva clave, cerrar sesión en todos lados,
# restablecer) invalida de golpe todos los tokens anteriores, aunque no hayan vencido.
def create_token(user_id: int, version: int = 0) -> str:
    return _encode({"sub": str(user_id), "v": version}, timedelta(days=SESSION_DAYS))


def decode_token(token: str) -> tuple[int, int] | None:
    claims = _decode(token)
    if claims is None or "purpose" in claims:  # un token de correo no sirve como sesión
        return None
    try:
        return int(claims["sub"]), int(claims.get("v", 0))
    except (KeyError, ValueError):
        return None


def create_purpose_token(user_id: int, purpose: str, version: int, minutes: float) -> str:
    return _encode({"sub": str(user_id), "v": version, "purpose": purpose}, timedelta(minutes=minutes))


def decode_purpose_token(token: str, purpose: str) -> tuple[int, int] | None:
    claims = _decode(token)
    if claims is None or claims.get("purpose") != purpose:
        return None
    try:
        return int(claims["sub"]), int(claims["v"])
    except (KeyError, ValueError):
        return None
