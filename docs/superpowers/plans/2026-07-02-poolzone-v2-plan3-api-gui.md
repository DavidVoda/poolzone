# Poolzone v2 — Plan 3: FastAPI backend + React admin (record)

**Status:** executed & complete 2026-07-02 (built inline under ponytail).

**Goal:** A working admin GUI to browse/edit products, edit pricing rules, and view/trigger sync + export jobs.

## Backend (`app/api/`)

- `deps.py` — request-scoped DB session (`get_db`).
- `schemas.py` — Pydantic: `ProductOut` (+ computed `sale_price`), `ProductUpdate` (owner-editable fields only), `MarginRuleOut/Update`, `JobRunOut`.
- `routers/products.py` — `GET /api/products` (search `q`, `active`, limit/offset), `GET/PATCH /api/products/{id}`. PATCH writes only owner fields; refresh after flush so DB-quantized numerics come back.
- `routers/pricing.py` — `GET /api/pricing/rules`, `PUT /api/pricing/rules/{id}`.
- `routers/jobs.py` — `GET /api/jobs`, `POST /api/jobs/export`, `POST /api/jobs/sync/{supplier}`.
- `main.py` — app, CORS for Vite dev (:5173), mounts `frontend/dist` if present.
- Tests: `tests/test_api.py` (9, TestClient with `get_db` overridden to the transactional fixture). Full suite 29 passed.

## Frontend (`frontend/`)

Vite + React + TS + Tailwind v4 + TanStack Query + react-router.
- `lib/api.ts` — hand-written typed client. `components/ui.tsx` — hand-rolled Button/Input/Card/Badge (shadcn-style classes).
- Pages: `Products` (search + table), `ProductDetail` (edit form), `Pricing` (rule rows), `Jobs` (history + Sync/Export buttons).
- Dev: `npm run dev` proxies `/api` → :8000. Prod: `npm run build` → `dist`, served by FastAPI.

## Ponytail decisions (deliberate)

- **Frontend is React, not HTMX.** User confirmed they'll keep building UI and want it to look good — that flips the lazy default; React earns its keep. (HTMX would have been right for a static admin.)
- **No OpenAPI codegen.** Hand-written ~30-line typed client. Add codegen when endpoint count makes maintaining types hurt.
- **No shadcn CLI/radix yet.** Hand-rolled primitives with shadcn class conventions; drop in real shadcn components when one needs radix behavior (dialog/dropdown).
- **Job triggers run synchronously.** A manual admin click that waits is fine at this scale. Move to FastAPI BackgroundTasks when the sync wait annoys.
- **ProductDetail reads via the list endpoint** (finds its row) instead of a dedicated GET — add a single-product GET when a product is deep-linked cold.
- **Categories page skipped** — table is empty until Plan 4 bootstrap.

## Remaining

- **Plan 4** — bootstrap (import current Upgates XML as ground truth; migrate `produkty_cenotvorba.xlsx` → margin/coefficient, `poolzone_categories.xlsx` → categories + `supplier_category_map`); categories XML export; GitHub Pages publish; cut-over (old scripts/libpoolzone → `archive/`). Then wire the scheduler (APScheduler, cron from config) + a Categories admin page.
