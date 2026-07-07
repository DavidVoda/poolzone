import { ArrowRight } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { Badge } from "@/components/ui/badge"
import { useT } from "@/lib/i18n"

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

// Outbound: Postgres → Upgates PRODUCTS XML.
// Mirrors app/export/upgates_xml.py (render_products). Keep in sync.
type OutRow = { db: string; xml: string; note?: string }

const OUT_ROWS: OutRow[] = [
  { db: "products.code", xml: "PRODUCT/CODE", note: "obchodní klíč" },
  { db: "products.title", xml: "DESCRIPTION[cs]/TITLE" },
  { db: "products.url_slug", xml: "DESCRIPTION[cs]/URL", note: "jen když je vyplněno" },
  { db: "product_images (url, ord)", xml: "IMAGES/IMAGE/URL", note: "seřazeno dle ord" },
  { db: "products.price_purchase", xml: "PRICE[cs]/PRICE_PURCHASE" },
  {
    db: "(odvozeno)",
    xml: "PRICE_COMMON + PRICELIST/PRICE_ORIGINAL",
    note: "prodejní cena = nákup × 1/(1−marže) × koeficient",
  },
  {
    db: "product_categories → category.upgates_code",
    xml: "CATEGORY/CODE + PRIMARY_YN",
    note: "seřazeno dle position; jen kategorie s upgates_code",
  },
  { db: "—", xml: "EAN", note: "záměrně prázdné — vyplněné EAN rozbije srovnávače cen" },
  { db: "products.ean", xml: "SUPPLIER_CODE", note: "EAN se přenáší sem místo do EAN" },
  { db: "products.stock", xml: "STOCK", note: "jen když je vyplněno" },
  { db: "products.weight", xml: "WEIGHT", note: "jen když je vyplněno" },
]

const OUT_STAGES = [
  { title: "Postgres", sub: "products (aktivní)", tone: "bg-green-100 text-green-700" },
  { title: "render_products()", sub: "upgates_xml.py", tone: "bg-emerald-100 text-emerald-700" },
  { title: "poolzone_products.xml", sub: "Upgates PRODUCTS", tone: "bg-emerald-100 text-emerald-700" },
  { title: "Upgates e-shop", sub: "import feed", tone: "bg-slate-100 text-slate-700" },
]

export default function FeedMapping() {
  const { t } = useT()
  return (
    <>
      <PageHeader title={t("Transformace feedu")} />

      <p className="mb-5 max-w-3xl text-sm text-muted-foreground">
        {t(
          "Jak se dodavatelský feed Pooltechnika (Heureka XML) mění na naši datovou strukturu. Stažení → parsování na",
        )}{" "}
        <code>ParsedProduct</code>{" "}
        {t("→ uložení do Postgres pravidlem create-full (nový produkt) / update-whitelist (existující).")}
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
              <th className="px-4 py-2 font-medium">{t("XML tag (SHOPITEM)")}</th>
              <th className="px-4 py-2 font-medium">ParsedProduct</th>
              <th className="px-4 py-2 font-medium">{t("Cíl v DB")}</th>
              <th className="px-4 py-2 font-medium">{t("Transformace / pravidlo")}</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((r) => (
              <tr key={r.parsed} className="border-t">
                <td className="px-4 py-2 font-mono text-xs">{r.xml}</td>
                <td className="px-4 py-2 font-mono text-xs text-sky-700">{r.parsed}</td>
                <td className={`px-4 py-2 font-mono text-xs ${r.unmapped ? "text-muted-foreground" : ""}`}>
                  {t(r.db)}
                </td>
                <td className="px-4 py-2 text-xs text-muted-foreground">
                  <div className="flex flex-wrap items-center gap-1.5">
                    {r.transform && <span>{t(r.transform)}</span>}
                    {r.whitelist && (
                      <Badge variant="secondary" className="bg-amber-100 text-amber-700">
                        {t("aktualizuje sync")}
                      </Badge>
                    )}
                    {r.createOnly && (
                      <Badge variant="secondary" className="bg-slate-100 text-slate-600">
                        {t("jen při vytvoření")}
                      </Badge>
                    )}
                    {r.unmapped && (
                      <Badge variant="secondary" className="bg-slate-100 text-slate-500">
                        {t("neukládá se sync")}
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
          <h3 className="mb-1 font-medium text-sky-800">{t("Nový produkt → create-full")}</h3>
          <p className="text-sm text-muted-foreground">
            {t("Kód ve feedu nemá odpovídající produkt: vytvoří se se")} <b>{t("vším")}</b>
            {t(", co feed poslal — název, EAN, výrobce, cena, sklad, hmotnost, dostupnost, obrázky a parametry.")}
          </p>
        </div>
        <div className="rounded-lg border bg-card p-4 shadow-sm">
          <h3 className="mb-1 font-medium text-sky-800">{t("Existující produkt → update-whitelist")}</h3>
          <p className="text-sm text-muted-foreground">
            {t("Přepíšou se")} <b>{t("pouze")}</b> {t("sloupce z whitelistu dodavatele (výchozí")}{" "}
            <code>stock</code>, <code>price_purchase</code>, <code>availability</code>
            {t("). Ruční úpravy obsahu (název, popisy, parametry, obrázky) sync nikdy nepřepíše.")}
          </p>
        </div>
      </div>

      <p className="mt-4 text-xs text-muted-foreground">
        {t("Chyba u jednoho produktu nikdy nezastaví běh — sbírá se do")}{" "}
        <code>job_runs.stats.errors</code>{" "}
        {t("a zobrazuje v sekci Úlohy.")}
      </p>

      {/* ── Outbound: DB → Upgates ─────────────────────────────── */}
      <h2 className="mt-10 mb-1 text-lg font-semibold text-emerald-800">{t("Výstup do Upgates")}</h2>
      <p className="mb-5 max-w-3xl text-sm text-muted-foreground">
        {t("Jak se naše data exportují do Upgates PRODUCTS XML. Jen aktivní produkty; export se přeskočí, pokud se od posledního běhu nic nezměnilo.")}
      </p>

      {/* Export pipeline stages */}
      <div className="mb-6 flex flex-wrap items-center gap-2 overflow-x-auto rounded-lg border bg-card p-4 shadow-sm">
        {OUT_STAGES.map((s, i) => (
          <div key={s.title} className="flex items-center gap-2">
            <div className={`rounded-md px-3 py-2 text-center ${s.tone}`}>
              <div className="text-sm font-medium">{s.title}</div>
              <div className="text-[11px] opacity-70">{t(s.sub)}</div>
            </div>
            {i < OUT_STAGES.length - 1 && <ArrowRight className="size-4 shrink-0 text-muted-foreground" />}
          </div>
        ))}
      </div>

      {/* Export field mapping */}
      <div className="overflow-x-auto rounded-lg border bg-card shadow-sm">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-emerald-50/60 text-left text-emerald-800">
              <th className="px-4 py-2 font-medium">{t("Zdroj v DB")}</th>
              <th className="px-4 py-2 font-medium">{t("Upgates XML tag")}</th>
              <th className="px-4 py-2 font-medium">{t("Transformace / pozn.")}</th>
            </tr>
          </thead>
          <tbody>
            {OUT_ROWS.map((r) => (
              <tr key={r.xml} className="border-t">
                <td className={`px-4 py-2 font-mono text-xs ${r.db === "—" || r.db === "(odvozeno)" ? "text-muted-foreground" : ""}`}>
                  {t(r.db)}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-emerald-700">{r.xml}</td>
                <td className="px-4 py-2 text-xs text-muted-foreground">{r.note && t(r.note)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
