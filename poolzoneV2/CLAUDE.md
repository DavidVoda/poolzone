# poolzoneV2 — admin middleware for poolzone.cz

Single FastAPI process + Postgres + React SPA. Middleware between supplier feeds and
the poolzone.cz Upgates e-shop: ingest supplier/eshop data, price it, export feeds.
Setup, run, and CLI commands live in `README.md` — read it first, this file is the map
and the rules.

## Layout

- `app/models.py` — SQLAlchemy models (the schema). One file, source of truth.
- `app/api/` — FastAPI. `main.py` wires routers + serves the built SPA. `routers/*` one per
  resource. `schemas.py` = Pydantic I/O. `deps.py` = request-scoped session (commits on
  success, rolls back on any exception). `filters.py` = `col:op:value` list-filter parser.
- `app/sync/` — ingest. `pipeline.py` = supplier feed upsert (create-full / update-whitelist).
  `suppliers/*` = per-supplier adapters (`fetch`+`parse`), registered in `suppliers/__init__.py`
  `ADAPTERS`. `poolzone.py` = eshop Upgates product+category import (GUI "Import dat").
- `app/export/upgates_xml.py` — writes the outbound eshop feed.
- `app/pricing.py` — margin resolution + sale-price formula.
- `app/migrations/` — Alembic. `scripts/bootstrap.py` — one-time legacy load.
- `frontend/` — React 19, Vite, Tailwind 4, shadcn/ui, TanStack Table/Query, TipTap. Czech UI.
- `tests/` — pytest, runs against a **separate** `poolzone_test` DB (see README).

## Invariants — do not break

- **Pricing formula lives in two places and must stay identical**: `app/pricing.py` and
  `frontend/src/lib/pricing.ts`. Sale (excl VAT) = `purchase / (1 - margin) * coefficient`,
  `ROUND_HALF_UP` to cents. Margin resolution order: explicit `product.margin_pct` →
  code-prefix rule (e.g. `AK` = Aseko) → global default. Change one file, change the other,
  update both test suites (`tests/test_pricing.py`, `pricing.test.ts`).
- **API types are generated**: after any router/schema change run `npm run api:types`
  (regenerates `frontend/src/lib/api-types.d.ts`). The typed client breaks silently otherwise.
- **Schema changes need an Alembic migration** (`alembic revision -m ...`, chain
  `down_revision` to current head). Tests use `create_all`, so a new *table* works without a
  migration but a new *column* on an existing table does not — the migration is still required
  for dev/prod.
- **Whitelist import semantics** (`app/sync/pipeline.py`, `app/sync/poolzone.py`): a NEW row is
  created with every field; an EXISTING row only has whitelisted fields overwritten. This
  protects operator hand-edits. Preserve it when touching import code.
- **Prices**: the eshop export carries *sale* prices only; purchase price comes from supplier
  feeds and sale is derived. Never import a sale price into `price_purchase`.

## Conventions

- Backend lint/format: **ruff** (line length 100). Frontend lint: **oxlint** (`npm run lint`).
- Product business key is `code`. Supplier-scoped uniqueness is `(supplier_id, code)`; the
  eshop `poolzone` import matches by `code` alone (cross-supplier).
- Jobs (sync/export/import) run **synchronously** on the admin click and record a `JobRun`.
  Fine at this scale; move to BackgroundTasks only if the wait actually hurts.
- Deliberate shortcuts are marked with `# ponytail:` comments naming the ceiling — grep them
  before assuming something is an oversight.
- Non-trivial logic ships with a runnable check (a `tests/test_*.py`), no heavy fixtures.

## Gotchas

- DB is on host port **5433** (not 5432). Default `DATABASE_URL` in `app/settings.py`.
- Run commands from `poolzoneV2/` with the venv (`./.venv/bin/...`); the repo root is a
  separate legacy tree with its own `tests/` and no `package.json`.
- The SPA catch-all in `main.py` serves `frontend/dist` — after a frontend change, `npm run
  build` before smoke-testing through uvicorn, or use the Vite dev server (`:5173`, proxies
  `/api`).
- **Feature-request pipeline** (`routers/feature_requests.py`): the backend only owns a
  guarded status state machine (`/transition`) — it does NOT run any agent. The operator
  flips a request to `ready_for_plan` / `ready_for_impl` in the UI; a local claude session
  runs the **`feature-runner`** skill, which dispatches a subagent per request (procedure
  in `.claude/skills/feature-pipeline/`) to plan/implement in the **current working tree,
  no commit**. Operator reviews the diff and commits by hand. (A periodic runner is a
  future note in the skill.) The old backend-spawns-`claude` runner is in
  `archive/agent/`.
