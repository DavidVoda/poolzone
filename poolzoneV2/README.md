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

## Sync a supplier (after seeding a `suppliers` row)

    ./.venv/bin/poolz sync pooltechnika

## Status

Plan 1 (foundation + sync) complete. Next: Plan 2 (pricing + Upgates XML export).
