# Poolzone Admin UI — Design Spec

**Date:** 2026-07-03
**Status:** Approved (brainstorm with visual companion)
**Author:** David Voda + Claude (Fable)
**Parent spec:** `2026-07-02-poolzone-middleware-v2-design.md` (§9 GUI) — this spec details the React admin it names.
**Mockups:** `.superpowers/brainstorm/97188-1783072058/content/` (shell-layout, visual-style, table-filtering, product-detail, component-plan-v2)

---

## 1. Purpose

Detailed UI design for the poolzoneV2 React admin: layout, visual style, component inventory, and per-screen blueprints for all six screens (four v1 + two later-phase). Used by e-shop operators; must feel modern and handle data-dense product tables.

Existing `frontend/` (Vite + React 19 + Tailwind 4 + TanStack Query, hand-rolled `ui.tsx`, top-nav shell, 4 rough pages) is the starting point; this spec replaces its shell and component approach.

## 2. Decisions (made during brainstorm)

| Topic | Decision |
|---|---|
| App shell | Light sidebar + slim topbar (global search ⌘K + job-status chip). Full-width content. |
| Visual style | Pool blue: white surfaces, sky-blue accents (Tailwind `sky` ramp), rounded cards, soft shadows. |
| Table filtering | Chip filter bar (Linear-style): "+ Filtr" → column → operator (=, ≠, >, <, obsahuje, prázdné) → value; removable chips; free-text search always visible; "Sloupce" show/hide menu. |
| Many columns | Horizontal scroll, sticky kód+název columns, column visibility persisted (localStorage). |
| Product detail | Separate screen, single scroll, sticky pricing sidebar with live sale-price calc. |
| Product peek | Row click opens right-half slide-over panel (`/?peek=:id`); full detail screen remains. |
| Scope | All 6 screens designed fully: Produkty, Kategorie, Ceny, Úlohy + Návrhy, Konkurence. |
| Long description editor | TipTap rich text with raw-HTML toggle. |
| Stack | shadcn/ui (copy-in, Radix + Tailwind 4) + TanStack Table (headless) + TipTap. Rejected: Mantine/MUI (fights Tailwind), extending hand-rolled ui.tsx (too much custom code). |
| UI language | Czech. |

## 3. App shell

```
┌─────────┬──────────────────────────────────────────┐
│ ◍ Poolz.│ [🔍 ⌘K search]              [PageActions] │
│ ▦ Produkty ────────────────────────────────────────│
│ 🗂 Kategorie                                        │
│ 💰 Ceny  │              <Outlet>                    │
│ ✨ Návrhy (badge: pending count)                    │
│ 📊 Konkurence                                       │
│ ⚙ Úlohy  │                                          │
│──────────│                                          │
│ ● sync OK 12:40 (JobStatusChip)                     │
└─────────┴──────────────────────────────────────────┘
```

Components: `AppShell`, `SidebarNav` (badge counts), `JobStatusChip` (polls latest job run; 5 s while running, else 60 s), `GlobalSearch` (⌘K palette — jumps to product by kód/název/EAN), `PageHeader` (title + actions slot).

## 4. Shared component library

- **`DataTable`** — TanStack Table wrapper: `FilterBar` (chips as above), `ColumnMenu` (show/hide, localStorage), sticky first columns, sort, pagination, row selection, loading/empty states. Server-side filter/sort/paginate; chips serialize to query params (e.g. `?filter=stock:gt:0`); one generic filter parser on the FastAPI products router.
- **Form kit** — `FormSection` (card + heading), `Field` wrappers over shadcn inputs, `RichTextEditor` (TipTap + raw-HTML toggle), `UnsavedChangesBar` (sticky bottom; guards route change and peek-row change with confirm).
- **Primitives** — `StatusBadge` (aktivní/job states/stock), `PriceCell` (Kč formatting, delta coloring), `ConfirmDialog`, `Toast`, `EmptyState` (with retry on query error), `TreeView` (categories), `DiffView` (phase 2).

## 5. Screens

### 5.1 Produkty `/`
`PageHeader` + `DataTable` (12+ columns: kód, název, dodavatel, výrobce, kategorie, sklad, dostupnost, nákupní cena, koeficient, marže, prodejní cena, aktivní…). Filter state in URL (shareable). Bulk row-select → aktivovat/deaktivovat.

**`ProductPeekPanel`** — row click opens right ~50 % slide-over; list stays interactive; ⎋ closes; ↑↓ walks rows; URL `/?peek=:id`. Contents: header (kód, název, StatusBadge, "⛶ Celý detail", ✕), image thumb + summary line (dodavatel, výrobce, sklad, dostupnost), `PricingCard` reuse with inline koef/marže edit + live prodejní cena, content-status line (popis ✓/✗ · SEO ✓/✗ · obrázky n), actions ([Uložit] [↻ Re-pull] [✨ Generovat popis]).

### 5.2 Detail produktu `/products/:id`
Single scroll. Header: kód + název + StatusBadge + actions (↻ Re-pull, ✨ Generovat popis, Uložit). Main column: `ContentSection` (název, krátký popis, TipTap dlouhý popis, SEO title/description/slug), `ParamsEditor` (název/hodnota/pořadí rows), `ImagesGrid` (URL previews, alt, pořadí), `CategoriesPicker` (tree + hlavní kategorie flag). Right: sticky `PricingCard` — nákupní cena, koeficient, marže override, resolved margin source shown (override / výrobce / globální), live computed prodejní cena. `RePullDialog`: fetch feed on demand → checkbox per field → apply picked fields.

### 5.3 Kategorie `/categories`
Two-pane: left `TreeView` (add/rename/move), right `CategoryForm` (název, SEO) + `SupplierMappingTable` (supplier_path → this category).

### 5.4 Ceny `/pricing`
`MarginDefaultsCard` (pricing_rules rows, editable: globální 35 % · Aseko 34 %) + `OverridesTable` (DataTable reuse: products with koef ≠ 1 or explicit marže; inline edit).

### 5.5 Úlohy `/jobs`
`TriggerBar` ([▶ Sync teď] [▶ Export teď] + next scheduled times) + `RunsTable` (druh, stav, trvání, stats summary) → `RunDetailDrawer` (full stats JSON, per-product error list).

### 5.6 Návrhy `/suggestions` (phase 2)
Chip filters (pole, stav) + `SuggestionCard` list = `DiffView` (current ↔ suggested) with [Přijmout] [Upravit a přijmout] [Odmítnout] [↻ Znovu s pokynem].

### 5.7 Konkurence `/competitors` (phase 2)
`ComparisonTable` (DataTable reuse): naše cena vs per-competitor columns (bazenonline, bazeny24, bazenyeshop, bazenyshop), delta badges, scrape age, [Navrhnout cenu] → creates suggestions row.

## 6. Data flow / state

- TanStack Query = only server state. No Redux/Zustand. UI state → URL params (filters, peek id) + localStorage (column visibility).
- API client generated from FastAPI OpenAPI schema via `openapi-typescript`; typed end to end.
- Mutations: no optimistic updates (single user) — invalidate + Toast.
- Live sale price computed client-side; formula mirrors `app/pricing.py` (one small function; fixture values shared with `test_pricing.py` keep them in lockstep).
- Polling: JobStatusChip/Jobs — 5 s while a run is `running`, else 60 s.

## 7. Error handling

- Query errors → `EmptyState` with retry (no blank screens). Mutation errors → Toast with server message.
- Client validation minimal (required, numeric ranges); FastAPI 422 field errors rendered under fields.
- `UnsavedChangesBar` blocks navigation (including peek row switch) with confirm.
- No conflict handling (single user, per parent spec non-goals).

## 8. File layout

```
frontend/src/
├── components/
│   ├── ui/            # shadcn primitives (button, input, dialog, …)
│   ├── data-table/    # DataTable, FilterBar, ColumnMenu
│   ├── form/          # FormSection, Field, RichTextEditor, UnsavedChangesBar
│   └── app/           # AppShell, SidebarNav, GlobalSearch, JobStatusChip,
│                      # StatusBadge, PriceCell, TreeView, DiffView, ProductPeekPanel
├── pages/             # Products, ProductDetail, Categories, Pricing, Jobs,
│                      # Suggestions, Competitors
├── lib/               # generated api client, utils, format (Kč, dates)
└── App.tsx            # routes
```

Existing `components/ui.tsx` and current pages are replaced; anything retired moves to `archive/` (never deleted).

## 9. Testing

Vitest + Testing Library:
- FilterBar chip → query-param serialization.
- PricingCard math against fixture values from `tests/test_pricing.py`.
- UnsavedChangesBar navigation guard.
- DataTable column visibility persistence.

No E2E in v1 — manual smoke on cut-over checklist instead (single user).

## 10. Backend touchpoints (small, this spec's only API changes)

- Generic filter/sort/paginate params on products router (powers FilterBar).
- Pending-suggestions count endpoint (sidebar badge; phase 2).
- Global search endpoint (kód/název/EAN prefix match).
