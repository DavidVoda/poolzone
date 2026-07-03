import { ArrowRight } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { Badge } from "@/components/ui/badge"

// Mirrors app/sync/suppliers/pooltechnika.py (parse) + app/sync/pipeline.py (upsert).
// Keep in sync if the adapter changes.

type Row = {
  xml: string
  parsed: string
  db: string
  transform?: string
  createOnly?: boolean // written only when the product is newly created
  whitelist?: boolean // also overwritten on existing products by default sync
  unmapped?: boolean // parsed but not persisted by sync
}

const ROWS: Row[] = [
  { xml: "ITEM_ID", parsed: "code", db: "products.code", transform: "povinné — bez něj se položka přeskočí" },
  { xml: "PRODUCTNAME", parsed: "title", db: "products.title", createOnly: true },
  { xml: "EAN", parsed: "ean", db: "products.ean", createOnly: true },
  { xml: "MANUFACTURER", parsed: "manufacturer", db: "products.manufacturer", createOnly: true },
  {
    xml: "PRICE_VAT",
    parsed: "price_purchase",
    db: "products.price_purchase",
    transform: "čárka→tečka, ÷ 1,21 (odečet DPH), zaokr. 2 des.",
    whitelist: true,
  },
  { xml: "stock_quantity", parsed: "stock", db: "products.stock", transform: "→ int", whitelist: true },
  {
    xml: "PARAM „Hmotnost“",
    parsed: "weight",
    db: "products.weight",
    transform: "jen číslice → gramy",
    createOnly: true,
  },
  { xml: "DELIVERY_DATE", parsed: "availability", db: "products.availability", whitelist: true },
  {
    xml: "IMGURL",
    parsed: "image_urls[]",
    db: "product_images (url, ord)",
    transform: "1 obrázek → pole",
    createOnly: true,
  },
  {
    xml: "PARAM (PARAM_NAME + VAL)",
    parsed: "params[]",
    db: "product_params (name, value, ord)",
    transform: "všechny PARAM řádky",
    createOnly: true,
  },
  { xml: "URL", parsed: "url", db: "— (neukládá se)", unmapped: true },
  {
    xml: "CATEGORYTEXT",
    parsed: "category_path",
    db: "— (mapuje se ručně)",
    transform: "přiřazení přes supplier_category_map",
    unmapped: true,
  },
]

const STAGES = [
  { title: "Pooltechnika feed", sub: "Heureka XML · <SHOPITEM>", tone: "bg-slate-100 text-slate-700" },
  { title: "parse()", sub: "pooltechnika.py", tone: "bg-sky-100 text-sky-700" },
  { title: "ParsedProduct", sub: "dataclass", tone: "bg-sky-100 text-sky-700" },
  { title: "run_sync()", sub: "create-full / update-whitelist", tone: "bg-sky-100 text-sky-700" },
  { title: "Postgres", sub: "products (+ params, images)", tone: "bg-green-100 text-green-700" },
]

export default function FeedMapping() {
  return (
    <>
      <PageHeader title="Transformace feedu" />

      <p className="mb-5 max-w-3xl text-sm text-muted-foreground">
        Jak se dodavatelský feed Pooltechnika (Heureka XML) mění na naši datovou strukturu. Stažení →
        parsování na <code>ParsedProduct</code> → uložení do Postgres pravidlem create-full (nový
        produkt) / update-whitelist (existující).
      </p>

      {/* Pipeline stages */}
      <div className="mb-6 flex flex-wrap items-center gap-2 overflow-x-auto rounded-lg border bg-card p-4 shadow-sm">
        {STAGES.map((s, i) => (
          <div key={s.title} className="flex items-center gap-2">
            <div className={`rounded-md px-3 py-2 text-center ${s.tone}`}>
              <div className="text-sm font-medium">{s.title}</div>
              <div className="text-[11px] opacity-70">{s.sub}</div>
            </div>
            {i < STAGES.length - 1 && <ArrowRight className="size-4 shrink-0 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {/* Field mapping */}
      <div className="overflow-x-auto rounded-lg border bg-card shadow-sm">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-sky-50/60 text-left text-sky-800">
              <th className="px-4 py-2 font-medium">XML tag (SHOPITEM)</th>
              <th className="px-4 py-2 font-medium">ParsedProduct</th>
              <th className="px-4 py-2 font-medium">Cíl v DB</th>
              <th className="px-4 py-2 font-medium">Transformace / pravidlo</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.parsed} className="border-t">
                <td className="px-4 py-2 font-mono text-xs">{r.xml}</td>
                <td className="px-4 py-2 font-mono text-xs text-sky-700">{r.parsed}</td>
                <td className={`px-4 py-2 font-mono text-xs ${r.unmapped ? "text-muted-foreground" : ""}`}>
                  {r.db}
                </td>
                <td className="px-4 py-2 text-xs text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {r.transform && <span>{r.transform}</span>}
                    {r.whitelist && (
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                        aktualizuje sync
                      </Badge>
                    )}
                    {r.createOnly && (
                      <Badge variant="secondary" className="bg-slate-100 text-slate-600">
                        jen při vytvoření
                      </Badge>
                    )}
                    {r.unmapped && (
                      <Badge variant="secondary" className="bg-slate-100 text-slate-500">
                        neukládá se sync
                      </Badge>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rule cards */}
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <h3 className="mb-1 font-medium text-sky-800">Nový produkt → create-full</h3>
          <p className="text-sm text-muted-foreground">
            Kód ve feedu nemá odpovídající produkt: vytvoří se se <b>vším</b>, co feed poslal — název,
            EAN, výrobce, cena, sklad, hmotnost, dostupnost, obrázky a parametry.
          </p>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <h3 className="mb-1 font-medium text-sky-800">Existující produkt → update-whitelist</h3>
          <p className="text-sm text-muted-foreground">
            Přepíšou se <b>pouze</b> sloupce z whitelistu dodavatele (výchozí{" "}
            <code>stock</code>, <code>price_purchase</code>, <code>availability</code>). Ruční úpravy
            obsahu (název, popisy, parametry, obrázky) sync nikdy nepřepíše.
          </p>
        </div>
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        Chyba u jednoho produktu nikdy nezastaví běh — sbírá se do <code>job_runs.stats.errors</code>{" "}
        a zobrazuje v sekci Úlohy.
      </p>
    </>
  )
}
