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
  if (p.margin_pct != null) return { margin: Number(p.margin_pct), source: "override" }
  for (const [prefix, margin] of Object.entries(rules)) {
    if (prefix !== "default" && p.code.startsWith(prefix)) return { margin, source: "prefix", prefix }
  }
  return { margin: rules.default, source: "default" }
}

export function salePrice(
  p: { code: string; price_purchase: string | null; coefficient: string; margin_pct: string | null },
  rules: MarginRules,
): number | null {
  if (p.price_purchase == null) return null
  const { margin } = resolveMargin(p, rules)
  const raw = (Number(p.price_purchase) / (1 - margin)) * Number(p.coefficient)
  return Math.round(raw * 100) / 100 // half-up on positive prices, matches ROUND_HALF_UP
}
