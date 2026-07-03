# Poolzone v2 — Plan 4: Data bootstrap (record)

**Status:** executed & complete 2026-07-02 (built inline under ponytail).

**Goal:** Load the current live data into the v2 DB so it becomes the source of truth: categories, products (from the current Upgates export), and per-product pricing from the legacy Excel.

**Scope changes from the original Plan 4 (per user):** no `archive/` move (cut-over deferred), **no GitHub Pages publisher** (GH Pages is being retired — not built), categories XML export deferred (no consumer yet). Scheduler + Categories admin page not in this plan.

## What was built

`scripts/bootstrap.py` — idempotent, IO split from pure logic:
- `parse_upgates_products(raw)` — Upgates `PRODUCT` XML → dicts (code, title, url, ean from `SUPPLIER_CODE`, purchase price, stock, weight, images, category codes).
- `category_rows` / `pricing_rows` — openpyxl readers → dicts.
- `load_categories` — creates `categories`, wires the parent tree via the Excel `ID kategorie`/`ID nadřazené kategorie`, builds `supplier_category_map` from `Pooltechnika ID kategorie` (dedup: a supplier path maps to one category, first wins).
- `load_products` — creates products (+ images + category links) under the pooltechnika supplier, skipping existing `(supplier, code)`.
- `apply_pricing` — sets `coefficient` from the Excel and `margin_pct` (AK prefix → 0.35, else 0.45), reproducing the old "listed in Excel" base margin.
- `ensure_default_rules` — seeds `pricing_rules` (default 0.35, AK 0.34).

Tests: `tests/test_bootstrap.py` (6) — parser, prefix margin, category tree + supplier map, idempotency, product↔category links, pricing apply.

## Test isolation fix (root cause)

Tests were sharing the dev DB, so loading real data would break every test that assumes small state. `tests/conftest.py` now runs against a dedicated `poolzone_test` database (override via `TEST_DATABASE_URL`); the dev `poolzone` DB holds the real bootstrap data untouched by the suite.

## Verification (real data)

- Bootstrap: **143 categories, 3789 products, 1008 priced** (~15 s). 3789 < 3871 XML rows = 82 duplicate CODEs skipped (legacy export repeats codes).
- Export at scale: **3789 products, 3298 with categories, ~1.6 s** (N+1 fix holds).
- **Price parity: exact.** Recomputed sale prices equal the old export's `PRICE_COMMON` (e.g. code 12309 → 3440.56 both). The 315 apparent mismatches in a first check were an artifact of duplicate CODEs in the legacy file (a `1.27` accessory sharing a code), not a pricing difference.
- Suite: 41 passed, ruff clean.

## Ponytail decisions

- **No GitHub Pages publisher** — retired; `run_export` just writes files. A publisher slots in when the new publish path (likely Upgates API) is chosen.
- **No archiving / cut-over** — old scripts + `libpoolzone` stay in place until the user decides.
- **Categories XML export deferred** — categories live in the DB (needed for links/sync); rendering the categories feed waits for a consumer.

## Remaining (not V1-blocking)

- New publish path (Upgates API pusher) + categories XML if that path needs it.
- APScheduler wiring (cron sync/export from config) — spec §10.
- Categories admin page in the React app.
- Cut-over + archiving of the old scripts, when the user is ready.
