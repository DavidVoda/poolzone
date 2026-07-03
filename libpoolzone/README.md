# libpoolzone

Shared Python package for the Poolzone platform.

## First-time setup

```bash
# 1. Python environment
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Postgres
cp .env.example .env
docker compose up -d postgres
docker exec poolzone-postgres psql -U poolzone -d poolzone -c "CREATE DATABASE poolzone_test;"

# 3. Schema
alembic upgrade head
DATABASE_URL="postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test" alembic upgrade head

# 4. Run tests
pytest
```

## Package layout

- `storage/` — SQLAlchemy models, engine, Alembic migrations.
- `catalog/` — service layer (products, categories, field locks). Higher-level code goes through here, not the ORM.
- `importers/`, `exporter/`, `seo/`, `pricing/` — populated in later milestones.

See `docs/superpowers/specs/2026-05-13-poolzone-platform-design.md` for the full design.
