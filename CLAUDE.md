# Finanzas personales (PWA + FastAPI)

App de finanzas personales, COP, para familia y amigos (~10 personas, cada una con sus datos, por invitación). Plan completo: `prompt-app-gastos-claude-code.md`.

## Reglas no negociables
1. Dinero: nunca `float`. Enteros COP (BigInteger), sin decimales. Formato `$ 1.234.567`.
2. Saldos de cuentas se CALCULAN desde los movimientos; no hay columna de saldo.
3. Las transferencias no cuentan como ingreso ni gasto en reportes.
4. Fechas de movimientos = `date`. "Hoy"/"mes actual" en America/Bogota (`app/timeutil.py`).
5. Seguridad: argon2, JWT en cookie httpOnly/Secure/SameSite, rate limit en login, CORS restringido, secretos en `.env`.
6. Lógica de negocio en `backend/app/services/`, separada de las rutas. Tests ANTES de implementar.
7. Interfaz en español.
8. Todo dato tiene dueño (`user_id`). El filtro es automático en `app/tenancy.py` y falla cerrado (sin usuario en la sesión lanza `TenantError`). No escribas `.where(user_id=…)` a mano ni uses subconsultas/alias sobre tablas con dueño. Registro solo por invitación (el primer usuario es admin).

## Comandos
- Backend (desde `backend/`): `uv run pytest`, `uv run ruff check .`, `uv run uvicorn app.main:app --reload`
- Frontend (desde `frontend/`): `npm test`, `npm run lint`, `npm run build`, `npm run dev`

## Trabajo
Una fase a la vez; al terminar: tests en verde, linters limpios, commit. Si algo no está en el documento, preguntar.
Windows: si `uv` falla con "Missing expected target directory", pasar `--python <ruta a cpython-3.12 de uv>`.
