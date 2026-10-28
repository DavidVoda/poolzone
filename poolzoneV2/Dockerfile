# Single image for Rosti Stacks: build the SPA, then serve it from FastAPI.

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml alembic.ini ./
COPY app ./app
# Editable install: main.py locates frontend/dist relative to its own file, so the
# code must stay in /app, not site-packages.
RUN pip install -e .
COPY --from=web /web/dist ./frontend/dist

EXPOSE 8000
# Migrate on every start (idempotent), then serve. Proxy headers: Rosti's proxy terminates TLS.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
