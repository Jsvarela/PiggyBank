# Una sola imagen: compila el frontend y lo sirve desde el backend (mismo origen => cookies simples).
FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
RUN pip install --no-cache-dir uv==0.13.0 && useradd --system --create-home app
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY --from=web /web/dist /app/static
ENV STATIC_DIR=/app/static PATH="/app/.venv/bin:$PATH"
USER app
# Render define $PORT. Las migraciones corren en cada arranque (alembic no repite las ya aplicadas).
# --proxy-headers: detrás del proxy de Render, la IP real del visitante viene en X-Forwarded-For;
# sin esto el límite de intentos de login lo compartiría todo el mundo (y un atacante podría bloquearte).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
