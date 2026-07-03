import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Play, Save } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PageHeader } from "@/components/app/PageHeader"
import { client, unwrap, type FeedConfig } from "@/lib/api"
import { formatDateTime } from "@/lib/format"

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

function FeedCard({ feed }: { feed: FeedConfig }) {
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
      toast.success("Uloženo")
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const run = useMutation({
    mutationFn: () =>
      unwrap(client.POST("/api/feeds/{kind}/run", { params: { path: { kind: feed.kind } } })),
    onSuccess: (stats) => {
      toast.success(`Import dokončen: ${JSON.stringify(stats)}`)
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const toggle = (f: string) =>
    setSelected((s) => (s.includes(f) ? s.filter((x) => x !== f) : [...s, f]))

  return (
    <div className="space-y-4 rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{KIND_LABELS[feed.kind] ?? feed.kind}</h3>
        <span className="text-sm text-muted-foreground">
          Poslední import: {formatDateTime(feed.last_run_at)}
        </span>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`url-${feed.kind}`}>URL zdroje</Label>
        <Input
          id={`url-${feed.kind}`}
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://…"
        />
      </div>

      <div className="space-y-2">
        <Label>Přepisovat pole (whitelist)</Label>
        <p className="text-xs text-muted-foreground">
          Zaškrtnutá pole se u existujících položek přepíší z feedu. Nezaškrtnutá zůstanou
          zachována. Nové položky se vždy vytvoří kompletní.
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {feed.available_fields.map((f) => (
            <label key={f} className="flex items-center gap-2 text-sm">
              <Checkbox checked={selected.includes(f)} onCheckedChange={() => toggle(f)} />
              {FIELD_LABELS[f] ?? f}
            </label>
          ))}
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <Button size="sm" variant="outline" onClick={() => save.mutate()} disabled={save.isPending}>
          <Save className="size-4" /> Uložit
        </Button>
        <Button size="sm" onClick={() => run.mutate()} disabled={run.isPending}>
          <Play className="size-4" /> {run.isPending ? "Import běží…" : "Aktualizovat teď"}
        </Button>
      </div>
    </div>
  )
}

export default function Feeds() {
  const { data: feeds } = useQuery({
    queryKey: ["feeds"],
    queryFn: () => unwrap(client.GET("/api/feeds")),
  })

  return (
    <>
      <PageHeader title="Import dat" />
      <div className="space-y-5">{feeds?.map((f) => <FeedCard key={f.kind} feed={f} />)}</div>
    </>
  )
}
