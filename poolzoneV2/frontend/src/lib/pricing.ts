export type MarginRules = Record<string, number> // keyed by code prefix, plus "default"

export type MarginSource =
  | { margin: number; source: "override" }
  | { margin: number; source: "prefix"; prefix: string }
  | { margin: number; source: "default" }

export function rulesFromApi(rules: { scope: string; match_value: string | null; margin_pct: string }[]): MarginRules {
  const out: MarginRules = {}
  for (const r of rules) out[r.scope === "default" ? "default" : (r.match_value ?? "")] = Number(r.margin_pct)
  return out
}

export function resolveMargin(p: { code: string; margin_pct: string | null }, rules: MarginRules): MarginSource {
  if (p.margin_pct != null && p.margin_pct !== "") return { margin: Number(p.margin_pct), source: "override" }
  // Longest matching prefix wins — deterministic regardless of JS object key ordering
  // (numeric-looking keys would otherwise be reordered ahead of insertion order).
  let best: { margin: number; prefix: string } | null = null
  for (const [prefix, margin] of Object.entries(rules)) {
    if (prefix !== "default" && p.code.startsWith(prefix) && (!best || prefix.length > best.prefix.length)) {
      best = { margin, prefix }
    }
  }
  if (best) return { margin: best.margin, source: "prefix", prefix: best.prefix }
  return { margin: rules.default, source: "default" }
}

/** Parse a decimal string; blank/invalid -> null (avoids Number("")===0 showing a fake 0). */
const num = (v: string | null): number | null => {
  if (v == null || v.trim() === "") return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

export function salePrice(
  p: { code: string; price_purchase: string | null; coefficient: string; margin_pct: string | null },
  rules: MarginRules,
): number | null {
  const purchase = num(p.price_purchase)
  const coef = num(p.coefficient)
  if (purchase == null || coef == null) return null
  const { margin } = resolveMargin(p, rules)
  const raw = (purchase / (1 - margin)) * coef
  // +epsilon nudge counters binary float representation so half-cents round up like
  // the backend's Decimal ROUND_HALF_UP (preview only; backend is authoritative on save).
  return Math.round((raw + 1e-9) * 100) / 100
}
