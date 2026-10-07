# Poolzone Admin UI — how to build with this system

A React 19 + **Tailwind CSS v4** admin UI built on **shadcn/ui** primitives, styled with a
sky-blue (pool) accent over a neutral shadcn base. The interface language is **Czech**.
Import every component from the global bundle (`window.PoolzoneUI.*`); the compiled CSS in
`styles.css` is already loaded.

## Wrapping & setup
- **The design-system primitives need no provider.** `Button`, `Badge`, `Input`, `Textarea`,
  `Label`, `Checkbox`, `Select`, `Dialog`, `Sheet`, `Table`, `Tooltip`, `Popover`,
  `DropdownMenu`, `Command`, and `StatusBadge` are styled purely by their utility classes —
  drop them straight into a page.
- **The app is light-only.** The root sets `color-scheme: light`; do not add a `dark` class —
  there is no dark theme.
- A few *application* components (`AppShell`, `GlobalSearch`, `JobStatusChip`) read React
  Router and TanStack Query context and will not render outside the real app — prefer the
  primitives above when composing new screens.

## Styling idiom — Tailwind v4 utilities over semantic tokens
Style with **Tailwind utility classes**, never inline hex or ad-hoc CSS. Colors come from
semantic tokens (defined as CSS variables, exposed as Tailwind color utilities). Use the
token utilities, not raw palette colors, so everything stays on-brand:

| Utility family | Real classes | Use for |
|---|---|---|
| Surfaces | `bg-background`, `bg-card`, `bg-popover`, `bg-muted`, `bg-sidebar` | page / panel / hover surfaces |
| Accent (pool blue) | `bg-primary`, `text-primary`, `text-primary-foreground`, `hover:bg-primary/90` | primary actions, active state |
| Neutral actions | `bg-secondary`, `bg-accent`, `text-accent-foreground` | secondary / hover |
| Danger | `bg-destructive`, `text-destructive` | destructive actions, errors |
| Text | `text-foreground`, `text-muted-foreground` | body / secondary text |
| Borders & shape | `border`, `border-input`, `rounded-md`, `rounded-lg`, `shadow-sm` | fields, cards |
| Focus | `ring-ring`, `focus-visible:ring-2` | focus rings |
| Layout | `flex`, `grid`, `gap-2`, `gap-4`, `px-4`, `py-2`, `space-y-4` | your own layout glue |

The underlying tokens (for reference; prefer the utilities above): `--primary` (sky-600),
`--primary-foreground`, `--background`, `--foreground`, `--card`, `--muted`,
`--muted-foreground`, `--border`, `--input`, `--ring`, `--secondary`, `--destructive`,
`--accent`, `--radius` (0.625rem).

## Component conventions
- **`Button`** — `variant`: `default` (blue), `secondary`, `outline`, `ghost`, `destructive`,
  `link`; `size`: `default`, `sm`, `lg`, `icon`. e.g. `<Button variant="outline" size="sm">`.
- **`Badge`** — `variant`: `default`, `secondary`, `destructive`, `outline`.
- **`StatusBadge`** — pass a `status` string; it renders a Czech, color-coded pill. Job
  statuses: `success`/`running`/`failed`/`skipped`; request statuses: `draft`/`ready_for_plan`/
  `planning`/`planned`/`ready_for_impl`/`implementing`/`implemented`.
- **Compound components** (`Select`, `DropdownMenu`, `Dialog`, `Sheet`, `Command`, `Table`)
  compose from sub-parts — e.g. `Select` + `SelectTrigger` + `SelectContent` + `SelectItem`.
  All sub-parts are on `window.PoolzoneUI`.
- **`PageHeader`** — `title` + optional `actions` node; standard page top bar.

## Where the truth lives
- `styles.css` — the entry the rendered design loads; it `@import`s `_ds_bundle.css` (all
  compiled component utilities + the `:root` token definitions). Read it before inventing
  classes.
- Per-component `components/<group>/<Name>/<Name>.prompt.md` — usage + props for each export.

## Idiomatic snippet
```tsx
// A titled panel with a primary action and a status pill — all real components + token utilities.
<div className="rounded-lg border bg-card p-4 shadow-sm">
  <PageHeader title="Produkty" actions={<Button size="sm">Nový</Button>} />
  <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
    <StatusBadge status="running" />
    <span>Synchronizace probíhá…</span>
  </div>
</div>
```
