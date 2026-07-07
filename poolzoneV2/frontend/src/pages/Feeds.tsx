import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CalendarClock, Play, RefreshCw, Save } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PageHeader } from "@/components/app/PageHeader"
import { StatusBadge } from "@/components/app/StatusBadge"
import { client, unwrap, type FeedConfig } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { useT } from "@/lib/i18n"

const KIND_LABELS: Record<string, string> = { products: "Produkty", categories: "Kategorie" }

const FIELD_LABELS: Record<string, string> = {
  title: "Název",
  short_description: "Krátký popis",
  long_description: "Dlouhý popis",
  ean: "EAN",
  manufacturer: "Výrobce",
  availability: "Dostupnost",
  stock: "Sklad",
  weight: "Hmotnost",
  active: "Aktivní",
  images: "Obrázky",
  params: "Parametry",
  categories: "Kategorie",
  name: "Název",
  seo_title: "SEO titulek",
  seo_description: "SEO popis",
  parent: "Nadřazená kategorie",
}

function FeedCard({ feed, busy }: { feed: FeedConfig; busy: boolean }) {
  const { t } = useT()
  const queryClient = useQueryClient()
  const [url, setUrl] = useState(feed.feed_url ?? "")
  const [selected, setSelected] = useState<string[]>(feed.update_whitelist)

  // Resync local edit state when the server copy changes (e.g. after a run).
  useEffect(() => {
    setUrl(feed.feed_url ?? "")
    setSelected(feed.update_whitelist)
  }, [feed.feed_url, feed.update_whitelist])

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["feeds"] })
    queryClient.invalidateQueries({ queryKey: ["jobs"] })
    queryClient.invalidateQueries({ queryKey: ["products"] })
  }

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        client.PATCH("/api/feeds/{kind}", {
          params: { path: { kind: feed.kind } },
          body: { feed_url: url, update_whitelist: selected },
        }),
      ),
    onSuccess: () => {
      toast.success(t("Uloženo"))
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const run = useMutation({
    mutationFn: () =>
      unwrap(client.POST("/api/feeds/{kind}/run", { params: { path: { kind: feed.kind } } })),
    onSuccess: (stats) => {
      toast.success(`${t("Import dokončen")}: ${JSON.stringify(stats)}`)
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const toggle = (f: string) =>
    setSelected((s) => (s.includes(f) ? s.filter((x) => x !== f) : [...s, f]))

  return (
    <div className="space-y-4 rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{t(KIND_LABELS[feed.kind] ?? feed.kind)}</h3>
        <span className="text-sm text-muted-foreground">
          {t("Poslední import")}: {formatDateTime(feed.last_run_at)}
        </span>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`url-${feed.kind}`}>{t("URL zdroje")}</Label>
        <Input
          id={`url-${feed.kind}`}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://…"
        />
      </div>

      <div className="space-y-2">
        <Label>{t("Přepisovat pole (whitelist)")}</Label>
        <p className="text-xs text-muted-foreground">
          {t(
            "Zaškrtnutá pole se u existujících položek přepíší z feedu. Nezaškrtnutá zůstanou zachována. Nové položky se vždy vytvoří kompletní.",
          )}
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {feed.available_fields.map((f) => (
            <label key={f} className="flex items-center gap-2 text-sm">
              <Checkbox checked={selected.includes(f)} onCheckedChange={() => toggle(f)} />
              {t(FIELD_LABELS[f] ?? f)}
            </label>
          ))}
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <Button size="sm" variant="outline" onClick={() => save.mutate()} disabled={save.isPending}>
          <Save className="size-4" /> {t("Uložit")}
        </Button>
        <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending || busy}>
          <Play className="size-4" /> {run.isPending ? t("Import běží…") : t("Aktualizovat teď")}
        </Button>
      </div>
    </div>
  )
}

function AutoRunInfo() {
  const { t } = useT()
  return (
    <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">
      <CalendarClock className="mt-0.5 size-5 shrink-0 text-amber-600" />
      <div>
        <div className="font-medium text-amber-900">{t("Automatické spouštění")}</div>
        <p className="text-amber-800">
          {t(
            "Žádná automatická úloha není nastavena — importy spouští operátor ručně tlačítky níže.",
          )}
        </p>
      </div>
    </div>
  )
}

// Section 1: supplier feed (Pooltechnika) → sync via the supplier adapter.
function PooltechnikaCard({ busy }: { busy: boolean }) {
  const { t } = useT()
  const queryClient = useQueryClient()

  const { data: suppliers } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => unwrap(client.GET("/api/suppliers")),
  })
  const supplier = suppliers?.find((s) => s.code === "pooltechnika")
  const [url, setUrl] = useState("")
  useEffect(() => setUrl(supplier?.feed_url ?? ""), [supplier?.feed_url])

  const { data: runs } = useQuery({
    queryKey: ["jobs", "sync", "latest"],
    queryFn: () =>
      unwrap(client.GET("/api/jobs", { params: { query: { kind: "sync", limit: 1 } } })),
    refetchInterval: (q) => (q.state.data?.[0]?.status === "running" ? 3_000 : false),
  })
  const last = runs?.[0]

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        client.PATCH("/api/suppliers/{code}", {
          params: { path: { code: "pooltechnika" } },
          body: { feed_url: url },
        }),
      ),
    onSuccess: () => {
      toast.success(t("Uloženo"))
      queryClient.invalidateQueries({ queryKey: ["suppliers"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const sync = useMutation({
    mutationFn: () =>
      unwrap(
        client.POST("/api/jobs/sync/{supplier_code}", {
          params: { path: { supplier_code: "pooltechnika" } },
        }),
      ),
    onSuccess: () => {
      toast.success(t("Synchronizace dokončena"))
      queryClient.invalidateQueries({ queryKey: ["jobs"] })
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  // The sync POST blocks until done; poll while pending so the running job surfaces.
  useEffect(() => {
    if (!sync.isPending) return
    const id = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["jobs", "sync", "latest"] })
      queryClient.invalidateQueries({ queryKey: ["jobs", "running"] })
    }, 1500)
    return () => clearInterval(id)
  }, [sync.isPending, queryClient])

  return (
    <div className="space-y-3 rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold">Pooltechnika</h3>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {last && <StatusBadge status={last.status} />}
          <span>
            {t("Poslední synchronizace")}: {formatDateTime(last?.finished_at ?? last?.started_at)}
          </span>
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        {t(
          "Stáhne dodavatelský feed (Heureka XML) a upsertne produkty pravidlem create-full / update-whitelist. Mapování polí viz Transformace.",
        )}
      </p>

      <div className="space-y-1.5">
        <Label htmlFor="pt-url">{t("URL zdroje")}</Label>
        <Input id="pt-url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
      </div>

      <div className="flex gap-2 pt-1">
        <Button size="sm" variant="outline" onClick={() => save.mutate()} disabled={save.isPending || !supplier}>
          <Save className="size-4" /> {t("Uložit")}
        </Button>
        <Button
          size="sm"
          onClick={() => sync.mutate()}
          disabled={sync.isPending || !url || busy}
        >
          <RefreshCw className="size-4" /> {sync.isPending ? t("Synchronizace běží…") : t("Synchronizovat teď")}
        </Button>
      </div>
    </div>
  )
}

export default function Feeds() {
  const { t } = useT()
  const { data: feeds } = useQuery({
    queryKey: ["feeds"],
    queryFn: () => unwrap(client.GET("/api/feeds")),
  })
  // Any running job disables every import trigger on the page (matches the 409 guard).
  const { data: latest } = useQuery({
    queryKey: ["jobs", "running"],
    queryFn: () => unwrap(client.GET("/api/jobs", { params: { query: { limit: 1 } } })),
    refetchInterval: (q) => (q.state.data?.[0]?.status === "running" ? 3_000 : false),
  })
  const busy = latest?.[0]?.status === "running"

  return (
    <>
      <PageHeader title={t("Import dat")} />
      <div className="space-y-6">
        <AutoRunInfo />

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t("Dodavatelský feed")}
          </h2>
          <PooltechnikaCard busy={busy} />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {t("E-shop Upgates (import)")}
          </h2>
          <div className="space-y-5">
            {feeds?.map((f) => <FeedCard key={f.kind} feed={f} busy={busy} />)}
          </div>
        </section>
      </div>
    </>
  )
}
