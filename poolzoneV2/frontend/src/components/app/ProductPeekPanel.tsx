import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, ExternalLink, X } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/app/StatusBadge"
import { PricingCard } from "@/components/app/PricingCard"
import { client, unwrap } from "@/lib/api"

type Props = {
  productId: number
  productIds: number[]
  onNavigate: (id: number) => void
  onClose: () => void
}

export function ProductPeekPanel({ productId, productIds, onNavigate, onClose }: Props) {
  const queryClient = useQueryClient()
  const [pricing, setPricing] = useState<{ coefficient?: string; margin_pct?: string | null }>({})

  const { data: product } = useQuery({
    queryKey: ["product", productId],
    queryFn: () =>
      unwrap(client.GET("/api/products/{product_id}", { params: { path: { product_id: productId } } })),
  })

  useEffect(() => setPricing({}), [productId])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT") return
      if (e.key === "Escape") onClose()
      const idx = productIds.indexOf(productId)
      if (e.key === "ArrowDown" && idx < productIds.length - 1) onNavigate(productIds[idx + 1])
      if (e.key === "ArrowUp" && idx > 0) onNavigate(productIds[idx - 1])
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [productId, productIds, onClose, onNavigate])

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        client.PATCH("/api/products/{product_id}", {
          params: { path: { product_id: productId } },
          body: pricing,
        }),
      ),
    onSuccess: () => {
      toast.success("Uloženo")
      setPricing({})
      queryClient.invalidateQueries({ queryKey: ["products"] })
      queryClient.invalidateQueries({ queryKey: ["product", productId] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (!product) return null
  const dirty = Object.keys(pricing).length > 0
  const image = product.images[0]

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex w-1/2 min-w-[420px] flex-col gap-4 overflow-y-auto border-l bg-background p-5 shadow-2xl">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-mono text-xs text-muted-foreground">{product.code}</div>
          <h2 className="text-lg font-semibold leading-tight">{product.title ?? "(bez názvu)"}</h2>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <Button asChild variant="outline" size="sm">
            <Link to={`/products/${product.id}`}>
              <ExternalLink className="size-4" /> Celý detail
            </Link>
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="flex gap-3 text-sm">
        {image && <img src={image.url} alt={image.alt ?? ""} className="size-20 rounded-md border object-cover" />}
        <div className="space-y-1 text-muted-foreground">
          <div>
            <StatusBadge status={product.active ? "active" : "inactive"} />{" "}
            {product.manufacturer && <span>· {product.manufacturer}</span>}
          </div>
          <div>
            Sklad {product.stock ?? "—"} · {product.availability ?? "—"}
          </div>
          <div className="flex items-center gap-2">
            Popis {product.long_description ? <Check className="size-3 text-green-600" /> : <X className="size-3 text-red-500" />}
            · SEO {product.seo_title ? <Check className="size-3 text-green-600" /> : <X className="size-3 text-red-500" />}
            · Obrázky {product.images.length}
          </div>
        </div>
      </div>

      <PricingCard
        code={product.code}
        pricePurchase={product.price_purchase}
        coefficient={pricing.coefficient ?? product.coefficient}
        marginPct={pricing.margin_pct !== undefined ? pricing.margin_pct : product.margin_pct}
        onChange={(patch) => setPricing((p) => ({ ...p, ...patch }))}
      />

      <div className="mt-auto flex items-center gap-2">
        <Button onClick={() => save.mutate()} disabled={!dirty || save.isPending}>
          Uložit
        </Button>
        <span className="text-xs text-muted-foreground">↑↓ další/předchozí · Esc zavře</span>
      </div>
    </div>
  )
}
