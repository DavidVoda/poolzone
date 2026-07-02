# Poolzone Middleware v2

Clean-restart rebuild. See `../docs/superpowers/specs/2026-07-02-poolzone-middleware-v2-design.md`.

## First-time setup

    python3.12 -m venv .venv
    ./.venv/bin/pip install -e ".[dev]"
    cp .env.example .env
    docker compose up -d
    ./.venv/bin/alembic upgrade head

## Test

    ./.venv/bin/pytest -q

## Sync / export from the CLI

    ./.venv/bin/poolz sync pooltechnika      # after seeding a suppliers row
    ./.venv/bin/poolz export --out-dir feeds

## Run the admin

    # API (serves built SPA if frontend/dist exists)
    ./.venv/bin/uvicorn app.api.main:app --reload --port 8000

    # Frontend dev (hot reload, proxies /api to :8000)
    cd frontend && npm install && npm run dev      # http://localhost:5173
    npm run build                                  # produces frontend/dist for prod

## Status

Plans 1–3 complete (foundation + sync, pricing + export, API + React admin).
Next: Plan 4 (bootstrap from current Upgates XML, Excel migrations, categories
XML, GitHub Pages publish, cut-over).
