# Poolzone Middleware v2 — Design Spec

**Date:** 2026-07-02
**Status:** Approved for implementation planning
**Author:** David Voda + Claude (Fable)
**Supersedes:** `2026-05-13-poolzone-platform-design.md` (judged over-engineered; implementation restarted clean)

---

## 1. Purpose

Middleware for managing poolzone.cz (hosted on Upgates): supplier data import, product management, Upgates XML export, AI-assisted content generation, and competition-based pricing — behind a single React admin GUI.

Replaces today's ad-hoc scripts (`createProductsForPoolzone.py`, `createCategoriesForPoolzone.py`, `getCategoriesFromPooltechnika.py`) and Excel roundtrips with one Postgres-backed application.

This spec deliberately simplifies the superseded 2026-05-13 design: one process instead of three, no field-lock engine, no i18n JSONB, no Streamlit. The implementation plan derived from this spec will be executed by lower models — every phase must be small, concrete, and independently verifiable.

## 2. Non-goals

- Multi-user / auth (single owner).
- Pulling orders or customer data from Upgates (one-way push).
- Image mirroring (URLs only).
- Multi-language content (CS only; plain text columns, not i18n structures).
- Message queues, microservices, separate worker processes.

## 3. Architecture

Single Python process + Postgres + React SPA.

```
supplier feeds ──► sync job ──► Postgres ──► export job ──► XML ──► GitHub Pages ──► Upgates (polls ~4h)
                                   ▲
                                   │
              React admin ──► FastAPI (same process)
```

- **One FastAPI app** serves the built React SPA and the JSON API.
- **APScheduler runs in-process.** Sync/export are plain Python functions. Triggered three ways: schedule (cron expressions from config), GUI button (FastAPI background task), CLI (`poolz sync`, `poolz export`).
- **Job status lives in DB** (`job_runs` table) — GUI polls it; no other coordination needed.
- **Postgres via docker-compose** (already in repo).

Rejected alternatives: separate worker process (second deployable for no gain at this scale); system crontab (owner wants schedule controlled by app config + manual GUI trigger).

## 4. Data model (v1)

9 tables. CS-only plain text columns. All product content columns nullable.

| Table | Columns (essence) |
|---|---|
| `suppliers` | `code`, `name`, `feed_url`, `update_whitelist` (text[], see §5), `enabled`, `last_synced_at` |
| `products` | `id`, `code` (Upgates CODE), `parent_id` (nullable, variants), `ean`, `manufacturer`, `supplier_id` (fk), `title`, `short_description`, `long_description`, `seo_title`, `seo_description`, `url_slug`, `stock`, `weight`, `availability`, `active`, `price_purchase`, `coefficient` (not null default 1.0), `margin_pct` (nullable), `note`, `created_at`, `updated_at` |
| `product_params` | `product_id`, `name`, `value`, `ord` |
| `product_images` | `product_id`, `url`, `alt`, `ord` (URLs only) |
| `categories` | `id`, `parent_id`, `name`, `seo_title`, `seo_description`, `upgates_code` |
| `product_categories` | `product_id`, `category_id`, `primary_yn`, `position` |
| `supplier_category_map` | `supplier_id`, `supplier_path`, `category_id` (replaces mapping column in old Excel) |
| `pricing_rules` | `scope` (`default` \| `manufacturer`), `match_value`, `margin_pct` — margin defaults only, 2 rows today |
| `job_runs` | `kind` (`sync` \| `export` \| later `generate`), `started_at`, `finished_at`, `status`, `stats` (jsonb), `error` |

Later AI phases add one table: `suggestions` (§8).

## 5. Sync — create-full / update-whitelist

Mirrors today's actual flow, formalized:

- **New product in feed** (no matching `products.code`): create with **everything** the supplier sent — title, descriptions, params, images, prices, categories.
- **Existing product**: update **only** whitelisted columns. Whitelist stored per supplier (`suppliers.update_whitelist`), default: `stock`, `price_purchase`, `availability`. Nothing else is ever touched by sync.
- **Escape hatch**: GUI "re-pull from supplier" action on a product — fetches the feed on demand and re-applies the fields the owner picks (for when supplier content improved and the owner wants it). No raw-feed snapshots are stored in v1.

No lock tables, no per-field diff engine. Owner edits are safe by construction: sync cannot write non-whitelisted columns of existing products.

Per-supplier code: one module `sync/suppliers/<code>.py` exposing `fetch() -> bytes` and `parse(raw) -> list[ParsedProduct]`. The shared upsert step enforces create-full/update-whitelist. Adding a supplier = one module (~100 lines) + one `suppliers` row + category mappings in GUI. Pooltechnika module is a port of the existing script's transform logic.

Per-product errors never abort a run: collected into `job_runs.stats.errors`, shown in GUI.

## 6. Export — Upgates XML

1. Read products (active) + categories from DB.
2. Compute sale prices (§7).
3. Render `poolzone_products.xml` + `poolzone_categories.xml` (same format as today's script output).
4. Smoke-validate structure.
5. Hash-compare against last published hash (in `job_runs.stats`) — skip publish if unchanged.
6. Publish: commit to the existing GitHub Pages feeds repo. `--dry-run` writes to local dir only.

Publishing sits behind one function so an **Upgates API pusher** can replace/augment it in a later phase without touching render logic.

## 7. Pricing (v1)

Coefficient and margin live on the product row; `pricing_rules` holds only margin defaults.

```python
margin = product.margin_pct                       # explicit override, or
        or manufacturer_default(product.manufacturer)  # 'Aseko' → 0.34
        or global_default                              # 0.35
price_sale = product.price_purchase * (1 / (1 - margin)) * product.coefficient
```

Migration from `produkty_cenotvorba.xlsx`: for each Excel row, set `coefficient` and set `margin_pct` explicitly (0.45 non-Aseko / 0.35 Aseko — preserving the current script's "listed in Excel" margin quirk as explicit data). Products not in Excel: coefficient 1.0, margin NULL. `Sleva`/`Příplatek` columns are read by no code; their info goes to a note field during migration and the Excel is archived.

Export prices must match today's script output exactly before cut-over (golden-file test).

## 8. Later phases (same plan, after v1 cut-over)

All AI output flows through one review mechanism — a `suggestions` table (`target_kind`, `target_id`, `field`, `suggested_value`, `status` pending/accepted/rejected, `model`, `created_at`, `reviewed_at`) and one review screen (current value vs. suggestion, Accept / Edit & Accept / Reject / Regenerate-with-hint). Accepted values are written to the product; sync can't overwrite them (whitelist model).

- **Description generator** — port of `descriptionGenerator/` (prompts, MANUAL.md template philosophy, PDF context extraction with per-URL caching, prompt caching). Template per product category as text files in `generation/templates/`; category → template mapping in DB. Targets products with empty `long_description`. Batch (scheduled) + single-product (GUI button).
- **SEO generator** — same pipeline, different templates and target fields (`seo_title`, `seo_description`, `url_slug`), driven by product attributes + files.
- **Pricing generator** — port existing competitor scrapers (bazenonline, bazeny24, bazenyeshop, bazenyshop) as `pricing/scrapers/<name>.py`; `competitor_prices` table (`product_id`, `competitor`, `url`, `price_with_vat`, `scraped_at`); scheduled scrape job; GUI screen comparing own vs. competitor prices; suggested price lands as a `suggestions` row, accept writes `margin_pct`/`coefficient`.
- **Upgates API pusher** — direct REST push behind the existing publish interface.

## 9. GUI (React)

Vite + TypeScript + shadcn/ui + TanStack Query. API client generated from FastAPI OpenAPI schema. Served as static build by FastAPI in production; Vite dev server during development.

V1 screens:

1. **Products** — list with search/filter (by supplier, category, active, missing-description); edit form (content, pricing fields, params, images, categories); "re-pull from supplier" action.
2. **Categories** — tree editor + supplier category mapping table.
3. **Pricing** — margin defaults editor; bulk view of product coefficient/margin overrides.
4. **Jobs** — run history from `job_runs` (status, stats, errors); manual trigger buttons (Sync now, Export now); next scheduled run times.

Later phases add: **Review queue** (suggestions) and **Competitor prices**.

## 10. Scheduling & config

- APScheduler in the FastAPI process. Job schedules are **config parameters** (env / `.env`): `SYNC_CRON`, `EXPORT_CRON` (cron expressions), per-job enable flags. Changing schedule = config change + restart; no schedule UI in v1.
- Manual triggers in GUI and CLI run the same functions.
- Overlap guard: a job checks `job_runs` for an in-progress run of its kind and skips (recorded as skipped).

## 11. Repo layout

```
poolzone/
├── pyproject.toml
├── docker-compose.yml          # postgres (+ app for prod-like runs)
├── app/                        # single Python package
│   ├── main.py                 # FastAPI + APScheduler startup
│   ├── settings.py             # env config incl. cron expressions
│   ├── db.py                   # engine, session, Base
│   ├── models.py               # SQLAlchemy models (one file until it hurts)
│   ├── migrations/             # Alembic
│   ├── api/                    # routers: products, categories, pricing, jobs, suppliers
│   ├── sync/
│   │   ├── pipeline.py         # shared upsert: create-full / update-whitelist
│   │   └── suppliers/
│   │       └── pooltechnika.py
│   ├── export/
│   │   ├── upgates_xml.py      # render + validate
│   │   └── publish.py          # github pages commit; --dry-run local
│   ├── pricing.py              # margin resolution + sale price math
│   ├── generation/             # later phases: generator, templates/, suggestions
│   └── cli.py                  # poolz sync|export (Typer or argparse)
├── frontend/                   # React SPA
├── scripts/                    # one-off: bootstrap, excel migrations
├── tests/
│   └── fixtures/               # checked-in feed XML + golden export files
└── archive/                    # old scripts, Excels, old libpoolzone (moved, never deleted)
```

## 12. Testing

- **Unit** — pricing math, whitelist upsert logic, XML rendering helpers.
- **Integration** — sync pipeline against a checked-in Pooltechnika XML fixture; asserts created/updated rows, whitelist respected, `job_runs` stats.
- **Golden-file** — export output byte-compared against fixture generated by the old script from the same input. Parity gate for cut-over.
- Hermetic: no live feed calls in tests.

## 13. Bootstrap & cut-over (one-time)

1. Schema up (Alembic), seed `suppliers` (Pooltechnika) + `pricing_rules` (2 default rows).
2. Import current Upgates export XML → `products` (+ params, images, categories). This is ground truth including all manual edits.
3. Migrate Excels: `produkty_cenotvorba.xlsx` → product `coefficient`/`margin_pct`; `poolzone_categories.xlsx` → `categories`; Pooltechnika mapping column → `supplier_category_map`.
4. Run first sync — verifies whitelist behavior against live data shape.
5. Run export — golden-file parity with old script output.
6. Cut-over: point scheduler at real feeds repo; move old scripts, Excels, XMLs, `BACKUP/`, `UTILITY/`, and old `libpoolzone/` to `archive/`. Moved, never deleted — owner verifies and deletes manually.

## 14. Implementation phasing (for the plan)

Sized for execution by lower models — each phase lands runnable and tested:

1. **Foundation** — project skeleton, settings, Postgres models + Alembic, docker-compose.
2. **Sync** — Pooltechnika module + shared pipeline + fixtures/tests.
3. **Pricing + Export** — price math, XML render, publish, golden-file parity.
4. **API + GUI v1** — FastAPI routers, React screens 1–4, scheduler wiring.
5. **Bootstrap & cut-over** — migration scripts, parity verification, archive.
6. **Description generator** (+ `suggestions` + review screen).
7. **SEO generator.**
8. **Pricing generator** (scrapers + competitor screen).
9. **Upgates API pusher** (optional, when XML latency hurts).
