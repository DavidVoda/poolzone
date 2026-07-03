import { useState } from "react"
import { useMutation } from "@tanstack/react-query"
import { RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { client, unwrap } from "@/lib/api"

/** Feed fields the owner may re-apply. Limited to what ProductUpdate accepts;
 * stock/prices/ean/manufacturer flow through sync, not manual re-pull. */
const APPLICABLE = [
  { key: "title", label: "Název" },
  { key: "params", label: "Parametry" },
  { key: "image_urls", label: "Obrázky" },
] as const

type FeedValues = {
  title: string | null
  ean: string | null
  manufacturer: string | null
  stock: number | null
  price_purchase: string | null
  availability: string | null
  params: { name: string; value: string }[]
  image_urls: string[]
}

type Applied = Partial<{
  title: string
  params: { name: string; value: string | null; ord: number }[]
  images: { url: string; alt: string | null; ord: number }[]
}>

export function RePullDialog({ productId, onApply }: { productId: number; onApply: (patch: Applied) => void }) {
  const [open, setOpen] = useState(false)
  const [checked, setChecked] = useState<Record<string, boolean>>({})

  const pull = useMutation({
    mutationFn: () =>
      unwrap(
        client.POST("/api/products/{product_id}/repull", {
          params: { path: { product_id: productId } },
        }),
      ) as Promise<FeedValues>,
    onError: (e: Error) => toast.error(e.message),
  })

  const feed = pull.data

  const apply = () => {
    if (!feed) return
    const patch: Applied = {}
    if (checked.title) patch.title = feed.title ?? ""
    if (checked.params) patch.params = feed.params.map((p, i) => ({ name: p.name, value: p.value, ord: i }))
    if (checked.image_urls) patch.images = feed.image_urls.map((url, i) => ({ url, alt: null, ord: i }))
    onApply(patch)
    setOpen(false)
    toast.info("Hodnoty přeneseny do formuláře — nezapomeňte uložit.")
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (o && !pull.data) pull.mutate()
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <RefreshCw className="size-4" /> Re-pull
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Znovu načíst z dodavatele</DialogTitle>
        </DialogHeader>
        {pull.isPending && <p className="text-sm text-muted-foreground">Stahuji feed…</p>}
        {feed && (
          <div className="space-y-2">
            {APPLICABLE.map(({ key, label }) => (
              <label key={key} className="flex items-start gap-2 rounded-md border p-2 text-sm">
                <Checkbox
                  checked={!!checked[key]}
                  onCheckedChange={(v) => setChecked((c) => ({ ...c, [key]: !!v }))}
                />
                <span>
                  <b>{label}:</b>{" "}
                  {key === "params"
                    ? `${feed.params.length} parametrů`
                    : key === "image_urls"
                      ? `${feed.image_urls.length} obrázků`
                      : String(feed[key] ?? "—")}
                </span>
              </label>
            ))}
            <p className="text-xs text-muted-foreground">
              Sklad {feed.stock ?? "—"} · nákup {feed.price_purchase ?? "—"} Kč · {feed.availability ?? "—"} — tyto
              hodnoty aktualizuje sync automaticky.
            </p>
          </div>
        )}
        <DialogFooter>
          <Button onClick={apply} disabled={!feed || !Object.values(checked).some(Boolean)}>
            Přenést vybrané
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
