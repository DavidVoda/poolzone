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

## Run everything (DB + API + frontend)

    make dev        # DB up, then API :8000 + Vite :5173 together (Ctrl-C stops both)

Pieces alone: `make db`, `make api`, `make web`.

## Run the admin

    # API (serves built SPA if frontend/dist exists)
    ./.venv/bin/uvicorn app.api.main:app --reload --port 8000

    # Frontend dev (hot reload, proxies /api to :8000)
    cd frontend && npm install && npm run dev      # http://localhost:5173
    npm run build                                  # produces frontend/dist for prod
    npm test                                       # vitest (pricing mirror, filters, unsaved guard)
    npm run api:types                              # regenerate src/lib/api-types.d.ts after backend schema changes

The admin UI is React 19 + shadcn/ui + TanStack Table/Query + TipTap (pool-blue theme,
Czech). API types are generated from the FastAPI OpenAPI schema — rerun `api:types` whenever
a router or schema changes so the typed client stays in sync.

## Bootstrap (one-time, loads legacy data into the DB)

    ./.venv/bin/python -m scripts.bootstrap        # reads ../poolzone_*.xml + ../*.xlsx

## Tests use a separate DB

Create it once: `docker compose exec -T db psql -U poolzone -c "CREATE DATABASE poolzone_test"`.
The suite runs against `poolzone_test`; the dev `poolzone` DB keeps bootstrap data.

## Status

Plans 1–4 complete (foundation + sync, pricing + export, API + React admin,
data bootstrap). DB holds real data: 143 categories, 3789 products.
Not done (not V1-blocking): new publish path (Upgates API), APScheduler
wiring, Categories admin page, cut-over/archiving of old scripts.

## Deploy (Rosti Stacks)

Single Docker image (SPA built in, migrations run on start) + Postgres, see
`Dockerfile` / `docker-compose.rosti.yml`. Docker Desktop must be running.

    ./deploy.sh init                       # once: login, create stack, write secrets, first deploy
    ./deploy.sh                            # every release
    ./deploy.sh seed-db                    # once: copy local DB to prod (overwrites!)
    ./deploy.sh admin you@x.cz 'password'  # first admin login
    ./deploy.sh logs

Secrets (`POSTGRES_PASSWORD`, `POOLZONE_SECRET_KEY`) live only on the VM in `/srv/stack/.env`.
