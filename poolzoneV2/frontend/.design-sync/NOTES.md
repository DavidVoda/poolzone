# design-sync notes — poolzoneV2/frontend

This "design system" is the **Vite admin app**, not a published component library.
There is no library `dist/` entry and no `.d.ts` exports, so the converter runs in
**synth-entry mode** (bundles from `src/`).

## Setup that makes the build work (don't re-derive)
- **Self-symlink required**: `ln -sfn "$PWD" node_modules/frontend` — the converter
  resolves `PKG_DIR = node_modules/<pkg>`, which doesn't exist for an app. The symlink
  points it at the real package so synth-from-src triggers. Recreate on a fresh clone
  (gitignored).
- **`srcDir: "src/components"`** — narrows the synth entry to components; without it the
  synth pulls in `pages/` and `App.tsx` (routing, not DS components).
- **`tsconfig` must be a clean, comment-free file** = `tsconfig.dssync.json` (committed),
  NOT `tsconfig.app.json`. Converter bug: `lib/bundle.mjs` `tsconfigPathsPlugin` strips
  block comments with `/\/\*[\s\S]*?\*\//`, which matches the `/*` inside the `"@/*"`
  paths key and runs to the `*/` of the real `/* Bundler mode */` comment — corrupting
  the JSON, so `JSON.parse` fails and the `@/` alias plugin is silently disabled →
  "Could not resolve @/…". A comment-free tsconfig (no `*/` anywhere) parses fine.
- **`cssEntry`** points at the built Tailwind CSS `dist/assets/index-<hash>.css`. The
  hash changes each `npm run build`; repoint it after a rebuild (or it 's stale).
  Components are Tailwind-utility-styled, so this compiled stylesheet is the real CSS.
- Paths in config are absolute to avoid base ambiguity through the symlink.

## Discovery
- 101 PascalCase exports discovered — many are shadcn compound sub-parts
  (`SelectTrigger`, `DropdownMenuContent`, `CommandInput`…) that only render inside their
  parent. They ship functional in the bundle; their standalone preview cards are floor
  cards unless authored as full parent compositions.

## Re-sync risks
- `cssEntry` hash is build-specific — rebuild the app and repoint before re-syncing.
- App components (`AppShell`, `GlobalSearch`, `JobStatusChip`, `ProductPeekPanel`,
  `RePullDialog`) read React Router / TanStack Query context — they render blank without a
  provider (`cfg.provider`) and are floor cards otherwise.
- Bundle inlines heavy deps (TanStack Table, TipTap, cmdk) — 1.87 MB, expected.

## Known issues
- **Switch** authored preview rendered an invisible track (only the label showed) — dropped
  to a floor card. Likely the `bg-input`/`bg-primary` track colors need investigating in the
  built CSS, or the Radix Switch thumb needs explicit sizing in this Tailwind 4 setup. Re-author
  once the track renders. (Checkbox works, so it's Switch-specific.)

## Authored (graded good) this run
Button, Badge, StatusBadge, Input, Textarea, Label, Checkbox, PageHeader. Remaining components
ship functional floor cards — authorable on any re-sync (grades/authored files carry forward).
