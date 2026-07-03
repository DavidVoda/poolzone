import { useEffect, useMemo, useState } from "react"
import { useParams } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/app/PageHeader"
import { PricingCard } from "@/components/app/PricingCard"
import { RePullDialog } from "@/components/app/RePullDialog"
import { StatusBadge } from "@/components/app/StatusBadge"
import { Field } from "@/components/form/Field"
import { FormSection } from "@/components/form/FormSection"
import { RichTextEditor } from "@/components/form/RichTextEditor"
import { UnsavedChangesBar } from "@/components/form/UnsavedChangesBar"
import { client, unwrap, type Category, type ProductDetail as ProductDetailT, type ProductUpdate } from "@/lib/api"

type FormState = {
  title: string
  short_description: string
  long_description: string
  seo_title: string
  seo_description: string
  url_slug: string
  note: string
  active: boolean
  coefficient: string
  margin_pct: string | null
  params: { name: string; value: string | null; ord: number }[]
  images: { url: string; alt: string | null; ord: number }[]
  categories: { category_id: number; primary_yn: boolean }[]
}

const toForm = (p: ProductDetailT): FormState => ({
  title: p.title ?? "",
  short_description: p.short_description ?? "",
  long_description: p.long_description ?? "",
  seo_title: p.seo_title ?? "",
  seo_description: p.seo_description ?? "",
  url_slug: p.url_slug ?? "",
  note: p.note ?? "",
  active: p.active,
  coefficient: p.coefficient,
  margin_pct: p.margin_pct,
  params: p.params,
  images: p.images,
  categories: p.categories,
})

export default function ProductDetail() {
  const { id } = useParams()
  const productId = Number(id)
  const queryClient = useQueryClient()

  const { data: product } = useQuery({
    queryKey: ["product", productId],
    queryFn: () =>
      unwrap(client.GET("/api/products/{product_id}", { params: { path: { product_id: productId } } })),
  })
  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => unwrap(client.GET("/api/categories")),
  })

  const [form, setForm] = useState<FormState | null>(null)
  useEffect(() => {
    if (product) setForm(toForm(product))
  }, [product])

  const dirty = useMemo(
    () => !!product && !!form && JSON.stringify(form) !== JSON.stringify(toForm(product)),
    [form, product],
  )

  const save = useMutation({
    mutationFn: (f: FormState) => {
      const body: ProductUpdate = {
        ...f,
        title: f.title || null,
        short_description: f.short_description || null,
        long_description: f.long_description || null,
        seo_title: f.seo_title || null,
        seo_description: f.seo_description || null,
        url_slug: f.url_slug || null,
        note: f.note || null,
      }
      return unwrap(
        client.PATCH("/api/products/{product_id}", { params: { path: { product_id: productId } }, body }),
      )
    },
    onSuccess: () => {
      toast.success("Uloženo")
      queryClient.invalidateQueries({ queryKey: ["product", productId] })
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (!product || !form) return <p className="text-muted-foreground">Načítám…</p>

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f))

  return (
    <>
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <span className="font-mono text-sm text-muted-foreground">{product.code}</span>
            {form.title || "(bez názvu)"}
            <StatusBadge status={form.active ? "active" : "inactive"} />
          </span>
        }
        actions={
          <>
            <label className="flex items-center gap-2 text-sm">
              Aktivní <Switch checked={form.active} onCheckedChange={(v) => set("active", v)} />
            </label>
            <RePullDialog productId={productId} onApply={(patch) => setForm((f) => (f ? { ...f, ...patch } : f))} />
            <Button onClick={() => save.mutate(form)} disabled={!dirty || save.isPending}>
              Uložit
            </Button>
          </>
        }
      />

      <div className="flex items-start gap-5">
        <div className="min-w-0 flex-1 space-y-5">
          <FormSection title="Obsah">
            <Field label="Název">
              <Input value={form.title} onChange={(e) => set("title", e.target.value)} />
            </Field>
            <Field label="Krátký popis">
              <Textarea value={form.short_description} onChange={(e) => set("short_description", e.target.value)} />
            </Field>
            <Field label="Dlouhý popis">
              <RichTextEditor value={form.long_description} onChange={(v) => set("long_description", v)} />
            </Field>
          </FormSection>

          <FormSection title="SEO">
            <Field label="SEO titulek">
              <Input value={form.seo_title} onChange={(e) => set("seo_title", e.target.value)} />
            </Field>
            <Field label="SEO popis">
              <Textarea value={form.seo_description} onChange={(e) => set("seo_description", e.target.value)} />
            </Field>
            <Field label="URL slug">
              <Input value={form.url_slug} onChange={(e) => set("url_slug", e.target.value)} />
            </Field>
          </FormSection>

          <FormSection
            title="Parametry"
            actions={
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  set("params", [...form.params, { name: "", value: "", ord: form.params.length }])
                }
              >
                <Plus className="size-4" /> Přidat
              </Button>
            }
          >
            {form.params.map((p, i) => (
              <div key={i} className="flex items-center gap-2">
                <Input
                  className="w-48"
                  placeholder="Název"
                  value={p.name}
                  onChange={(e) =>
                    set("params", form.params.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))
                  }
                />
                <Input
                  placeholder="Hodnota"
                  value={p.value ?? ""}
                  onChange={(e) =>
                    set("params", form.params.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))
                  }
                />
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={i === 0}
                  onClick={() => {
                    const next = [...form.params]
                    ;[next[i - 1], next[i]] = [next[i], next[i - 1]]
                    set("params", next.map((x, j) => ({ ...x, ord: j })))
                  }}
                >
                  <ArrowUp className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={i === form.params.length - 1}
                  onClick={() => {
                    const next = [...form.params]
                    ;[next[i], next[i + 1]] = [next[i + 1], next[i]]
                    set("params", next.map((x, j) => ({ ...x, ord: j })))
                  }}
                >
                  <ArrowDown className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() =>
                    set("params", form.params.filter((_, j) => j !== i).map((x, j) => ({ ...x, ord: j })))
                  }
                >
                  <Trash2 className="size-4 text-red-500" />
                </Button>
              </div>
            ))}
          </FormSection>

          <FormSection
            title="Obrázky"
            actions={
              <Button
                variant="outline"
                size="sm"
                onClick={() => set("images", [...form.images, { url: "", alt: "", ord: form.images.length }])}
              >
                <Plus className="size-4" /> Přidat
              </Button>
            }
          >
            <div className="grid grid-cols-2 gap-3">
              {form.images.map((img, i) => (
                <div key={i} className="flex gap-2 rounded-md border p-2">
                  {img.url && <img src={img.url} alt={img.alt ?? ""} className="size-16 rounded object-cover" />}
                  <div className="min-w-0 flex-1 space-y-1">
                    <Input
                      placeholder="URL"
                      value={img.url}
                      onChange={(e) =>
                        set("images", form.images.map((x, j) => (j === i ? { ...x, url: e.target.value } : x)))
                      }
                    />
                    <div className="flex gap-1">
                      <Input
                        placeholder="Alt"
                        value={img.alt ?? ""}
                        onChange={(e) =>
                          set("images", form.images.map((x, j) => (j === i ? { ...x, alt: e.target.value } : x)))
                        }
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          set("images", form.images.filter((_, j) => j !== i).map((x, j) => ({ ...x, ord: j })))
                        }
                      >
                        <Trash2 className="size-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </FormSection>

          <FormSection title="Kategorie">
            <CategoryChecklist
              categories={categories ?? []}
              value={form.categories}
              onChange={(v) => set("categories", v)}
            />
          </FormSection>

          <FormSection title="Poznámka">
            <Textarea value={form.note} onChange={(e) => set("note", e.target.value)} />
          </FormSection>
        </div>

        <div className="sticky top-5 w-72 shrink-0">
          <PricingCard
            code={product.code}
            pricePurchase={product.price_purchase}
            coefficient={form.coefficient}
            marginPct={form.margin_pct}
            onChange={(patch) => setForm((f) => (f ? { ...f, ...patch } : f))}
          />
        </div>
      </div>

      <UnsavedChangesBar
        dirty={dirty}
        saving={save.isPending}
        onSave={() => save.mutate(form)}
        onDiscard={() => setForm(toForm(product))}
      />
    </>
  )
}

function CategoryChecklist({
  categories,
  value,
  onChange,
}: {
  categories: Category[]
  value: { category_id: number; primary_yn: boolean }[]
  onChange: (v: { category_id: number; primary_yn: boolean }[]) => void
}) {
  const byParent = new Map<number | null, Category[]>()
  categories.forEach((c) => {
    const list = byParent.get(c.parent_id) ?? []
    list.push(c)
    byParent.set(c.parent_id, list)
  })

  const render = (parentId: number | null, depth: number): React.ReactNode =>
    (byParent.get(parentId) ?? []).map((c) => {
      const entry = value.find((v) => v.category_id === c.id)
      return (
        <div key={c.id}>
          <div className="flex items-center gap-2 py-0.5 text-sm" style={{ paddingLeft: depth * 20 }}>
            <Checkbox
              checked={!!entry}
              onCheckedChange={(v) =>
                onChange(
                  v
                    ? [...value, { category_id: c.id, primary_yn: value.length === 0 }]
                    : value.filter((x) => x.category_id !== c.id),
                )
              }
            />
            {c.name}
            {entry && (
              <label className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
                <input
                  type="radio"
                  name="primary-category"
                  checked={entry.primary_yn}
                  onChange={() =>
                    onChange(value.map((x) => ({ ...x, primary_yn: x.category_id === c.id })))
                  }
                />
                hlavní
              </label>
            )}
          </div>
          {render(c.id, depth + 1)}
        </div>
      )
    })

  return <div>{render(null, 0)}</div>
}
