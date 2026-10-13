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

## Tests y linters
```bash
cd backend && uv run pytest && uv run ruff check .
cd frontend && npm test && npm run lint && npm run build
```
