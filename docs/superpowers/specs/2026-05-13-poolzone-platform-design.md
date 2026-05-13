# Poolzone Platform — Design Spec

**Date:** 2026-05-13
**Status:** Approved for implementation planning
**Author:** David Voda + Claude

---

## 1. Purpose

Today's Poolzone tooling is a collection of ad-hoc Python scripts that read a Pooltechnika XML feed, apply price/category transforms via Excel files, and emit Upgates-compatible XML for static hosting. Separate tools (description generator, pricing Streamlit app) operate on the same data through file roundtrips.

The goal is to consolidate this into a **modular Python platform** with a single source of truth (Postgres), pluggable supplier importers, an audited export pipeline, AI-assisted SEO with human review, and a React admin — all designed so today's solo-local deployment can move to cloud / multi-user later without a rewrite.

## 2. Non-goals

- Multi-user/auth (single user today; design with clean boundaries so it can be added).
- Pulling orders or customer data back from Upgates (one-way push only).
- Mirroring product images to own storage (URLs only; mirroring is a possible follow-up).
- Replacing Upgates as the storefront.
- Microservices, message queues, Kubernetes — overkill for the scale.

## 3. High-level architecture

Modular monolith. One Python codebase (`libpoolzone`) consumed by three processes that share one Postgres database.

```
                EXTERNAL: Pooltechnika feed · future suppliers · competitor sites · Anthropic
                                              │
                                              ▼
       ┌───────────────────────────── libpoolzone (shared package) ─────────────────────────────┐
       │   catalog  ·  importers  ·  exporter  ·  seo  ·  pricing  ·  storage (SQLAlchemy/PG)   │
       └────────────┬─────────────────────┬───────────────────────┬───────────────────────────-─┘
                    │                     │                       │
                    ▼                     ▼                       ▼
              API process           Worker process         Streamlit process
              (FastAPI +            (APScheduler +         (pricing analysis,
              React SPA)            ad-hoc jobs)           ported to React later)
                    │
                    ▼
              React SPA (Vite + TS + TanStack Query + shadcn/ui)
                                              │
                                              ▼
         Worker writes XML  →  GitHub Pages (or any static host)  →  Upgates polls every ~4h
```

**Three processes, one codebase:**
- **API** — FastAPI serves the React build + JSON endpoints.
- **Worker** — APScheduler runs scheduled jobs (imports, exports, SEO batches, competitor scraping) and ad-hoc jobs triggered from the admin.
- **Streamlit** — pricing analysis tool, ported to read/write the central DB (replaces today's CSV roundtrip). Migrated to React in a later phase.
- **CLI (`poolz …`)** — thin wrapper around the same services for ad-hoc human ops.

**Module boundaries are strict.** Nothing in `importers` reads from `exporter`. Cross-module calls go through `catalog`. This is what lets you extract a module into its own service later if needed.

**Upgates integration is one-way push via static XML.** Worker regenerates two XML files and pushes them to a published path (GitHub Pages today). Upgates polls on its own ~4h schedule. No outbound API calls into Upgates from the platform.

## 4. Data model

### 4.1 Core tables

| Table | Purpose |
|---|---|
| `suppliers` | Registry of suppliers (Pooltechnika today, more later). Fields: `code`, `name`, `adapter_key`, `feed_url`, `auth` (jsonb), `last_synced_at`, `enabled`. |
| `supplier_products` | Last raw payload pulled from each supplier per `supplier_code`, as JSONB. Used for diffing on next sync. Links to a `products` row when matched. |
| `supplier_category_mappings` | Maps a supplier's category path string to a `categories.id`. Replaces "Pooltechnika ID kategorie" column in the old Excel. |
| `products` | Master catalog. See §4.2. |
| `product_field_locks` | `(product_id, field_path)` rows. If a row exists, importers skip that field. See §4.3. |
| `product_images` | `(product_id, url, alt, ord)`. URLs only — no mirroring. |
| `product_parameters` | `(product_id, name_i18n, value_i18n)`. Multilingual JSONB. |
| `product_files` | `(product_id, url, kind)` where `kind` ∈ {`pdf_manual`, `datasheet`, …}. |
| `categories` | Tree (self-referential `parent_id`). Includes multilingual name + SEO meta JSONB. |
| `product_categories` | M:N join with `primary_yn` and `position`. |
| `pricing_rules` | Replaces `produkty_cenotvorba.xlsx`. Scope = `supplier` or `product`. Fields: `margin_pct`, `coefficient`, `notes`. |
| `competitor_prices` | `(product_id, competitor_name, url, price_with_vat, scraped_at)`. |
| `seo_suggestions` | AI-generated content awaiting review. See §7. |
| `sync_runs` | Audit log for every import / export / SEO / scrape batch. |

### 4.2 `products` table

Single table for both standalone products and parent+variant structures. `parent_id` is self-referential nullable: NULL = standalone or parent; set = variant of parent.

Columns:
- Identity: `id`, `code` (Upgates CODE), `parent_id`, `ean`, `supplier_code`, `manufacturer`
- Logistics: `stock`, `weight`, `active`, `show`
- Multilingual content (JSONB, `{lang: value}`): `titles`, `short_descriptions`, `long_descriptions`, `urls`, `seo_titles`, `seo_descriptions`, `seo_keywords`
- Pricing: `price_purchase`, `price_common`, `price_original`
- Provenance: `primary_supplier_id` (fk)
- Timestamps: `created_at`, `updated_at`

**Multilingual via JSONB** (vs separate translations table) — adding a language is a no-op schema-wise. CS only today.

### 4.3 Field-level locks

`product_field_locks` is a separate table keyed by `(product_id, field_path)`. Field path is a dot-delimited string referencing a settable location, e.g.:

- `price.common`
- `descriptions.cs.long`
- `seo.cs.title`
- `categories.primary`

If a row exists, the supplier importer's `apply()` step skips that field for that product. Adding a new lockable field requires zero importer changes — the field path is just a new string.

Locks are created in three ways:
1. **Manual** — user toggles a lock in the admin UI.
2. **Auto on SEO accept** — accepting an AI suggestion locks that field (so the next sync doesn't overwrite the approved copy).
3. **Auto on price edit** — committing a new price from the pricing Streamlit auto-locks `price.common`.
4. **Auto during bootstrap** — see §10 step 5.

## 5. Importer framework

### 5.1 Adapter interface

Each supplier is a class implementing:

```python
class SupplierAdapter(Protocol):
    code: str                                    # e.g. "pooltechnika"
    def fetch(self) -> bytes: ...
    def parse(self, raw: bytes) -> Iterable[ParsedProduct]: ...
    def map_categories(self, supplier_path: str) -> list[CategoryRef]: ...
```

Adapters return a common `ParsedProduct` dataclass — see spec source for the full field list. The raw payload is also returned and stored as JSONB for diffing.

### 5.2 Shared pipeline

The pipeline is the only writer of supplier-sourced changes. Steps:

1. `fetch()` — adapter pulls supplier data
2. `parse()` — adapter normalizes to `ParsedProduct`
3. `snapshot()` — upsert into `supplier_products`
4. `match()` — link `supplier_product` → `products` row (by code, or create new)
5. `diff()` — compute per-field changes between supplier snapshot and current product
6. `apply()` — for each change: if `product_field_locks` has a matching row, skip; else write. Increment stats.
7. `record()` — append to `sync_runs` with full stats (`{products_seen, updated, locked_skips, errors, …}`).

Pricing math is **not** in the adapter — the adapter only returns `price_purchase` (purchase price excl VAT). Final sale prices are computed by the exporter from `pricing_rules`.

### 5.3 Adding a new supplier

= one adapter file (~150 lines) + one row in `suppliers` + category mappings (managed in admin UI). Zero changes to pipeline, locks, exporter, or admin.

### 5.4 Multi-supplier sourcing

`supplier_products` is a separate table per (supplier, supplier_code), so one `products` row can be linked from multiple suppliers (e.g. same EAN from two suppliers). Foundation for "buy from cheaper supplier today" later, though out of scope for v1.

## 6. Exporter

### 6.1 Pipeline

`libpoolzone/exporter/upgates.py`:
1. `snapshot()` — read products + categories from DB
2. `apply_pricing()` — resolve `pricing_rules` per product, compute `price_common` and `price_original`
3. `render_xml()` — build `poolzone_categories.xml` + `poolzone_products.xml` (only `active` products)
4. `validate()` — XSD validation if available, smoke checks otherwise
5. `publish()` — push files via configured `PublishTarget`
6. `record()` — append to `sync_runs`

### 6.2 Pluggable publish target

```python
class PublishTarget(Protocol):
    def publish(self, files: dict[str, bytes]) -> str: ...
```

Concrete implementations:
- `GitHubPagesPublisher` — commits files to the configured feeds repo (today's flow).
- `LocalPathPublisher` — writes to `./public/feeds/` for dev (point Upgates at ngrok/cloudflared during testing).
- `S3Publisher` — added later if hosting changes.

### 6.3 Pricing resolution

```python
def resolve_pricing(product) -> PricingRule:
    # most-specific wins
    return (
        pricing_rules.get(scope="product", product_code=product.code)
        or pricing_rules.get(scope="supplier", supplier_id=product.primary_supplier_id)
        or DEFAULT_RULE
    )

final = product.price_purchase * (1 / (1 - rule.margin_pct)) * rule.coefficient
```

Migration: a one-off script reads `produkty_cenotvorba.xlsx` and writes rows into `pricing_rules`. The Excel is then moved to `archive/` (see §10).

### 6.4 Triggers

- **Scheduled** — every 2h, regenerate XML if anything has changed.
- **After every successful import** — worker chains `sync → export`.
- **Manual** — "Regenerate Upgates XML" button in admin + `poolz export upgates` CLI.

### 6.5 Diff guard

Exporter computes SHA-256 of the rendered XML. If identical to the last published hash (stored in `sync_runs`), skip the push. Avoids empty commits in the feeds repo.

## 7. SEO module

### 7.1 Generation flow

`libpoolzone/seo/`:
1. `select()` — pick targets (products and/or categories matching criteria, e.g. "missing long_description")
2. `gather()` — pull product fields + parameters + PDF text (cached per URL) + peer products in same category for context
3. `choose_template()` — pump / electrolysis / chemical / category-generic
4. `generate()` — call Claude with the cached system prompt + per-target user message
5. `stash()` — write a row to `seo_suggestions` (status=`pending`)
6. `record()` — append to `sync_runs`

Generated content **never** reaches `products` directly. It always goes through the review queue.

### 7.2 `seo_suggestions` table

| Column | Notes |
|---|---|
| `id` | pk |
| `target_kind` | `"product"` \| `"category"` |
| `target_id` | fk to `products` or `categories` |
| `field_path` | e.g. `"descriptions.cs.long"`, `"seo.cs.title"` |
| `suggested_value` | text / jsonb |
| `template_used` | `"pump"` \| `"electrolysis"` \| `"category-generic"` \| … |
| `model` | e.g. `"claude-sonnet-4-6"` |
| `prompt_hash` | dedupe identical inputs |
| `generated_at` | timestamp |
| `status` | `"pending"` \| `"accepted"` \| `"rejected"` \| `"superseded"` |
| `reviewed_by`, `reviewed_at` | audit |

Append-only history — superseded suggestions are kept for traceability.

### 7.3 Review UI (React admin)

Side-by-side: current DB value vs. AI suggestion. Actions: **Accept** / **Edit & Accept** / **Reject** / **Regenerate (with hint)**.

**Accept auto-locks the field** by inserting into `product_field_locks` so the next supplier sync can't overwrite the approved copy.

### 7.4 Operating modes

- **Bulk batch** — worker job ("generate SEO for all products with no long_description"). Runs overnight, queue ready for morning review.
- **On-demand single** — admin button on product page, synchronous (~10–30 s).
- **Regenerate with hint** — reviewer rejects + writes a one-line hint; re-runs with hint injected into prompt.

### 7.5 What stays from today

- The full Czech system prompt with section template (🔧 ⚙️ 🛡️ 🔌 🏊 🟢 …)
- Pump / electrolysis variants
- PDF context extraction with per-URL caching
- Ephemeral system-prompt caching across batch calls
- The MANUAL.md template philosophy

### 7.6 What changes

- Input is the DB, not an Upgates export XML file
- Output is `seo_suggestions`, not an import XML file
- SEO meta fields (title, meta_description, keywords, URL) added alongside long/short descriptions
- Same pipeline handles category-level SEO (different template + target table)
- Templates live as text files in `libpoolzone/seo/templates/` (one file per product-type variant). Adding a "spa heater" template = adding a new file + registering it in a small dispatch dict — no other code change.

## 8. Pricing module

Split into **rules** (math, used by exporter) and **analysis** (Streamlit, ported to use DB).

```
libpoolzone/pricing/
├── rules.py        # resolve(product) → PricingRule  (used by exporter)
├── analysis.py     # market stats, competitor diffs  (powers Streamlit)
└── scrapers/       # per-competitor HTML scrapers (refactor existing into adapter pattern)
    ├── base.py
    ├── bazenonline.py
    ├── bazeny24.py
    ├── bazenyeshop.py
    └── bazenyshop.py

apps/streamlit_pricing/
└── app.py          # thin shell — calls libpoolzone.pricing functions
                    # reads from products + competitor_prices
                    # commits price changes back to products (auto-locks price.common)
```

Changes from today:
- **Competitor URLs leave the CSV** and live in the DB (linked to `products`), edited in the React admin.
- **Scraping runs on a schedule in the worker** (daily). Streamlit becomes a pure consumer/editor — no longer triggers scrapes at click time.
- **Committing a new price auto-locks `price.common`** — same convention as accepted SEO.
- **React port later** — same `libpoolzone.pricing` functions, new UI. No reimplementation.

## 9. Scheduler & worker

Single worker process, APScheduler. Job definitions in code; run config (cron expressions, enable flags) editable in admin.

Default schedule (overridable):

| Time (daily) | Job |
|---|---|
| 03:00 | Sync supplier `pooltechnika` |
| 03:30 | Scrape competitor prices |
| 04:00 | Export Upgates XML |
| 07:00 | Batch-generate SEO suggestions for new/incomplete products |
| every 2h | Re-export Upgates XML if anything changed |

Ad-hoc queue (admin + CLI):
- "Sync supplier X now"
- "Regenerate XML now"
- "Generate SEO for selected products"
- "Re-scrape competitor prices for product Y"

**Concurrency:** sequential per job kind via a single executor. No two imports running at once. Predictable and cheap.

**Idempotency:** all jobs check "is another run of me already in progress?" via `sync_runs` before starting.

**Observability:** worker exposes a small HTTP endpoint with `/health` and `/jobs` (next run times). Admin "Jobs" page reads it.

## 10. Bootstrap plan (one-time)

1. **Stand up infra** — Postgres via Docker, Alembic init, baseline schema migration.
2. **Seed reference data** — insert `suppliers` (Pooltechnika), migrate `produkty_cenotvorba.xlsx` → `pricing_rules`, migrate `poolzone_categories.xlsx` → `categories` tree with SEO meta fields.
3. **Build `supplier_category_mappings`** — migrate the "Pooltechnika ID kategorie" column from the Excel.
4. **Bootstrap products** — import the current Upgates export XML (full Upgates state, including all manual edits) into `products`. This is the ground truth.
5. **Run a Pooltechnika sync with locks empty** — verifies the diff/apply pipeline. Anywhere Upgates already had a value that differs from the supplier feed, auto-create a `product_field_locks` row. This bootstrap heuristic spares you from setting 2000+ locks by hand.
6. **Wire publisher to existing GitHub Pages feeds repo** — first export should produce near-byte-identical XML to today's.
7. **Cut-over** — once parity is confirmed, move the old scripts and Excels to `archive/`:
   - `createProductsForPoolzone.py`
   - `createCategoriesForPoolzone.py`
   - `getCategoriesFromPooltechnika.py`
   - `produkty_cenotvorba.xlsx`
   - `poolzone_categories.xlsx`
   - `pooltechnika_categories.xlsx` / `.xml`
   - `poolzone_categories.xml`
   - `poolzone_products.xml`
   - the BACKUP/ folder
   - the UTILITY/ folder

   **Files are moved, not deleted.** David removes them manually after verifying nothing references them.

## 11. Repo layout

```
poolzone/
├── pyproject.toml                  # one Python project, multiple entry points
├── docker-compose.yml              # postgres, api, worker, streamlit
├── .devcontainer/                  # already exists
│
├── libpoolzone/                    # shared package — everyone imports from here
│   ├── catalog/                    # products, categories, locks — service layer
│   ├── importers/
│   │   ├── pipeline.py             # the 7-step shared pipeline
│   │   └── adapters/
│   │       └── pooltechnika.py
│   ├── exporter/
│   │   ├── upgates.py              # XML render
│   │   └── publishers/             # github_pages.py, local.py, s3.py
│   ├── seo/
│   │   ├── generator.py            # Claude calls (prompt + caching)
│   │   └── templates/              # pump.txt, electrolysis.txt, category_generic.txt
│   ├── pricing/
│   │   ├── rules.py
│   │   ├── analysis.py
│   │   └── scrapers/
│   ├── storage/                    # SQLAlchemy models + Alembic migrations
│   └── settings.py                 # config (env vars, paths)
│
├── apps/
│   ├── api/                        # FastAPI — serves React + JSON
│   │   ├── main.py
│   │   └── routers/                # products, categories, suppliers, jobs, seo, pricing
│   ├── worker/                     # APScheduler + job functions
│   │   └── main.py
│   ├── cli/                        # `poolz …` commands (Typer)
│   │   └── main.py
│   └── streamlit_pricing/          # legacy-style Streamlit page (port to React later)
│       └── app.py
│
├── frontend/                       # React + Vite + TS + TanStack Query + shadcn/ui
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── api/                    # auto-generated client from FastAPI OpenAPI
│   └── package.json
│
├── feeds/                          # local copy of published XMLs (gitignored)
├── archive/                        # retired scripts & Excels (created during cut-over)
│
└── tests/
    ├── unit/
    ├── integration/                # importer pipeline against real Pooltechnika XML
    └── fixtures/
```

- **One Python project** (`pyproject.toml`), multiple entry points (`apps/*/main.py`). No submodule wrangling, no path hacks.
- **React is its own folder** with its own `package.json`. Built artifacts served by the FastAPI app in production; Vite dev server in development.
- **FastAPI OpenAPI → typed React client** auto-generated. No hand-written API types.
- **Existing code becomes adapter logic + fixtures** — the Pooltechnika XML transform seeds `adapters/pooltechnika.py`; the description generator becomes `libpoolzone/seo/generator.py`.

## 12. Error handling

- **Importer errors** never abort a run: per-product try/except, errors collected in `sync_runs.stats.errors`, surfaced in admin.
- **Exporter validates** XML structure before publishing (XSD if available, smoke checks otherwise). Bad XML never reaches the feeds repo.
- **Claude failures** in SEO are per-product: failed one is queued for retry; the batch continues.
- **Publisher failures** mark the export run as failed and surface in admin. Next scheduled run retries automatically.

## 13. Testing strategy

- **Unit tests** — pure logic: pricing math (`resolve_pricing`), lock resolution (`is_locked`), XML renderers, prompt builders.
- **Integration tests** — full importer pipeline against a checked-in Pooltechnika XML fixture. Asserts resulting DB state (products created/updated, locks respected, sync_run stats correct).
- **Snapshot tests** — exporter output against a golden XML fixture. Diff alert on changes — forces conscious updates.
- **No tests against live Pooltechnika feed** — fixture-based only, so the test suite is hermetic.

## 14. Deployment shape

### 14.1 Local (today, primary target)

`docker-compose.yml` brings up:
- `postgres`
- `api` (FastAPI + serves built React)
- `worker` (APScheduler)
- `streamlit` (pricing analysis)

Frontend dev: `cd frontend && npm run dev` (Vite hot reload).

### 14.2 Cloud (future, design-supported)

- Postgres → managed (Railway, Supabase, Neon)
- API + Worker → single small VPS or Railway/Fly.io
- React static build served by a CDN or by the API
- Same Docker Compose, different env vars

The single-user assumption is the main thing to revisit when going multi-user (add auth middleware on API, user table, etc.).

## 15. Out of scope (explicit follow-ups)

- Multi-user / auth / roles
- Image mirroring to own storage
- Two-way sync with Upgates (pulling orders)
- React port of the pricing module
- Multi-language storefront beyond CS
- "Buy from cheapest supplier" automation (the data model supports it; the logic is not in v1)
- JSON-LD structured data generation
- Internal-linking / cross-sell suggestions

## 16. Glossary

- **Adapter** — supplier-specific class that fetches + parses a supplier feed.
- **Field path** — dot-delimited string identifying a settable location on a product (`"price.common"`).
- **Lock** — a row in `product_field_locks` that prevents supplier sync from overwriting a field.
- **Publish target** — pluggable class that takes XML files and puts them somewhere Upgates can poll (GitHub Pages, S3, local path).
- **Sync run** — a single execution of an importer / exporter / SEO / scrape job, recorded for audit.
- **Suggestion** — AI-generated content sitting in a review queue, not yet applied to a product.
