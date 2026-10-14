"""Restablece la contraseña de alguien desde tu computador, sin necesidad de correo.

Uso (apuntando a la base de datos de producción):
    DATABASE_URL="postgresql://..." uv run python -m app.reset_password [correo]

Con una sola persona registrada el correo es opcional; con varias hay que indicarlo.
"""

import getpass
import sys

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.services.auth import set_password


def main() -> None:
    with SessionLocal() as db:
        if len(sys.argv) > 1:
            user = db.scalar(select(User).where(User.email == sys.argv[1].lower()))
            if user is None:
                sys.exit(f"No hay nadie registrado con el correo {sys.argv[1]}.")
        else:
            users = db.scalars(select(User)).all()
            if not users:
                sys.exit("No hay ningún usuario registrado.")
            if len(users) > 1:
                sys.exit("Hay varias personas: indica el correo. Ej.: python -m app.reset_password persona@correo.com")
            user = users[0]
        password = getpass.getpass(f"Contraseña nueva para {user.email}: ")
        if len(password) < 8:
            sys.exit("Debe tener al menos 8 caracteres.")
        set_password(db, user, password)  # también cierra las sesiones abiertas de esa persona
        print("Listo. Inicia sesión con la contraseña nueva.")


if __name__ == "__main__":
    main()
