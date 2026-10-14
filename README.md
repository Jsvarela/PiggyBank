# Finanzas

PWA de finanzas personales. Backend FastAPI (`backend/`), frontend React + Vite (`frontend/`).

## Correr en local
Requisitos: [uv](https://docs.astral.sh/uv/) y Node 20+.

```bash
# Backend (http://localhost:8000, docs en /docs)
cd backend
cp .env.example .env
uv run alembic upgrade head          # crea las tablas
uv run python -m app.seed            # categorías por defecto (--demo agrega datos de ejemplo)
uv run uvicorn app.main:app --reload

# Frontend (http://localhost:5173, proxy de /api al backend)
cd frontend
npm install
npm run dev
```

## Probar la interfaz con datos extremos (solo desarrollo)
Textos larguísimos, montos de 12 cifras, cuentas con emoji, listas vacías o de 1.500 filas. Usa una base desechable:
```bash
cd backend
DATABASE_URL=sqlite:///./worst.db uv run python -m app.seed_worst worst   # o: empty | one | huge
DATABASE_URL=sqlite:///./worst.db uv run uvicorn app.main:app --port 8000
```
Entra con `worst@localhost.test` (la contraseña está en `app/seed_worst.py`). Revisa cada pantalla a 320 px y con la letra al 200 %.

## Despliegue
Ver [DEPLOY.md](DEPLOY.md): Render + Neon, gratis, un solo servicio.

## Tests y linters
```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm test && npm run lint && npm run build
```
