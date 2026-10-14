from slowapi import Limiter
from slowapi.util import get_remote_address

# Tope general por IP para toda la API; las rutas sensibles (login, correo...) fijan uno más estricto.
limiter = Limiter(key_func=get_remote_address, default_limits=["300/minute"])
