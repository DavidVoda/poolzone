import { useQuery } from "@tanstack/react-query"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { client, unwrap } from "@/lib/api"
import { formatKc, formatPct } from "@/lib/format"
import { resolveMargin, rulesFromApi, salePrice } from "@/lib/pricing"

export function useMarginRules() {
  return useQuery({
    queryKey: ["pricing-rules"],
    queryFn: async () => rulesFromApi(await unwrap(client.GET("/api/pricing/rules"))),
  })
}

type Props = {
  code: string
  pricePurchase: string | null
  coefficient: string
  marginPct: string | null
  onChange: (patch: { coefficient?: string; margin_pct?: string | null }) => void
}

export function PricingCard({ code, pricePurchase, coefficient, marginPct, onChange }: Props) {
  const { data: rules } = useMarginRules()

  const resolved = rules ? resolveMargin({ code, margin_pct: marginPct }, rules) : null
  const price = rules
    ? salePrice({ code, price_purchase: pricePurchase, coefficient, margin_pct: marginPct }, rules)
    : null

  return (
    <div className="space-y-3 rounded-lg border bg-card p-4 shadow-sm">
      <h3 className="font-medium text-sky-800">Ceny</h3>
      <div className="text-sm text-muted-foreground">
        Nákupní cena <span className="float-right font-medium text-foreground">{formatKc(pricePurchase)}</span>
      </div>
      <div className="space-y-1">
        <Label htmlFor="coef">Koeficient</Label>
        <Input id="coef" value={coefficient} onChange={(e) => onChange({ coefficient: e.target.value })} />
      </div>
      <div className="space-y-1">
        <Label htmlFor="margin">Marže (např. 0.35, prázdné = výchozí)</Label>
        <Input
          id="margin"
          value={marginPct ?? ""}
          placeholder={
            resolved && resolved.source !== "override"
              ? `${formatPct(resolved.margin)} (${resolved.source === "prefix" ? `prefix ${resolved.prefix}` : "výchozí"})`
              : ""
          }
          onChange={(e) => onChange({ margin_pct: e.target.value === "" ? null : e.target.value })}
        />
      </div>
      <div className="rounded-md bg-accent px-3 py-2 text-accent-foreground">
        Prodejní cena <span className="float-right font-semibold">{formatKc(price)}</span>
      </div>
      {resolved && (
        <p className="text-xs text-muted-foreground">
          Použitá marže: {formatPct(resolved.margin)}{" "}
          {resolved.source === "override"
            ? "(vlastní)"
            : resolved.source === "prefix"
              ? `(pravidlo ${resolved.prefix})`
              : "(globální výchozí)"}
        </p>
      )}
    </div>
  )
}
