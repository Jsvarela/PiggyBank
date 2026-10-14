"""Restablece la contraseña desde tu computador, sin necesidad de correo.

Uso (apuntando a la base de datos de producción):
    DATABASE_URL="postgresql://..." uv run python -m app.reset_password
"""

import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.services.auth import set_password


def main() -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User))
        if user is None:
            sys.exit("No hay ningún usuario registrado.")
        password = getpass.getpass(f"Contraseña nueva para {user.email}: ")
        if len(password) < 8:
            sys.exit("Debe tener al menos 8 caracteres.")
        set_password(db, user, password)  # también cierra las sesiones abiertas
        print("Listo. Inicia sesión con la contraseña nueva.")


if __name__ == "__main__":
    main()
