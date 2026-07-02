# Poolzone v2 — Plan 2: Pricing + Upgates Export (record)

**Status:** executed & complete 2026-07-02 (built inline under ponytail, not micro-stepped like Plan 1).

**Goal:** Compute sale prices from per-product margin/coefficient and render active products to Upgates PRODUCTS XML.

## What was built

- `app/pricing.py` — `load_margin_rules(session)`, `resolve_margin(product, rules)`, `sale_price(product, rules)`.
  Formula: `purchase * 1/(1-margin) * coefficient`, rounded to 2 dp.
  Margin resolution: explicit `product.margin_pct` wins; else code prefix `AK` → Aseko rule (0.34); else default (0.35).
  **`AK` is an ITEM_ID prefix, not the manufacturer field** — matches the old script.
- `app/export/upgates_xml.py` — `render_products(session, rules) -> bytes` (active only; EAN blanked, value in `SUPPLIER_CODE`; PRICE_PURCHASE/PRICE_COMMON/PRICE_ORIGINAL; categories from `product_categories` via `Category.upgates_code`). `run_export(session, out_dir)` writes `poolzone_products.xml`, SHA-256 hash-skips unchanged output, records an export `JobRun`.
- `poolz export [--out-dir feeds]` CLI command.
- Tests: `tests/test_pricing.py` (6), `tests/test_export.py` (4). Full suite 20 passed.

## Ponytail deviations from spec §6/§7 (deliberate)

- **Golden test is semantic, not byte-parity.** Old script emits raw float (`118.46153846153845`); byte-comparing chases float formatting. Tests parse the XML and assert fields + price to 2 dp. Prices are rounded to cents (old kept full float precision — Upgates rounds to currency anyway). If David wants exact old-value parity, revisit.
- **Categories XML deferred to Plan 4.** `categories` table is empty until bootstrap, and the old category XML format (ACTIVE_YN, SHOW_IN_MENU_YN, CDATA DESCRIPTION_TEXT, keywords) is richer than the v2 `Category` model. Build it against real data in bootstrap.
- **No publisher abstraction.** `run_export` writes files to a dir. GitHub Pages commit/push → wire in Plan 4 cut-over (or when the real feeds repo is connected). No Protocol + 3 implementations.
- **No overlap guard on export.** Hash-skip prevents redundant writes; export is fast/idempotent.

## Remaining V1 plans

- **Plan 3** — FastAPI + React GUI (Products, Categories, Pricing, Jobs).
- **Plan 4** — bootstrap (import current Upgates XML as ground truth; migrate `produkty_cenotvorba.xlsx` → margin/coefficient, `poolzone_categories.xlsx` → categories; category-map); categories XML export; GitHub Pages publish; cut-over (old scripts/libpoolzone → `archive/`).
