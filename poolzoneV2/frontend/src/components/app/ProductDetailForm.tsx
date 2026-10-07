import { useEffect, useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { PricingCard } from "@/components/app/PricingCard"
import { RePullDialog } from "@/components/app/RePullDialog"
import { StatusBadge } from "@/components/app/StatusBadge"
import { Field } from "@/components/form/Field"
import { FormSection } from "@/components/form/FormSection"
import { RichTextEditor } from "@/components/form/RichTextEditor"
import { UnsavedChangesBar } from "@/components/form/UnsavedChangesBar"
import { client, unwrap, type Category, type ProductDetail as ProductDetailT, type ProductUpdate } from "@/lib/api"
import { useT } from "@/lib/i18n"
import { cn } from "@/lib/utils"

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

export type ProductDetailFormProps = {
  productId: number
  variant?: "page" | "modal"
  /** Called with current dirty state so a controlling modal can guard close. */
  onDirtyChange?: (dirty: boolean) => void
}

export function ProductDetailForm({ productId, variant = "page", onDirtyChange }: ProductDetailFormProps) {
  const { t } = useT()
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
  // Seed the form once per product id. Keying on product identity would let a
  // background refetch (window focus) silently overwrite unsaved edits.
  useEffect(() => {
    if (product) setForm(toForm(product))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id])

  const dirty = useMemo(
    () => !!product && !!form && JSON.stringify(form) !== JSON.stringify(toForm(product)),
    [form, product],
  )

  useEffect(() => onDirtyChange?.(dirty), [dirty, onDirtyChange])

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
      toast.success(t("Uloženo"))
      queryClient.invalidateQueries({ queryKey: ["product", productId] })
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (!product || !form) return <p className="text-muted-foreground">{t("Načítám…")}</p>

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((f) => (f ? { ...f, [key]: value } : f))

  const modal = variant === "modal"

  return (
    <div className={cn(modal && "flex h-full min-h-0 flex-col")}>
      <div
        className={cn(
          "flex items-center justify-between gap-4",
          modal ? "shrink-0 border-b px-6 py-4 pr-14" : "mb-4",
        )}
      >
        <h2 className="flex min-w-0 items-center gap-3 font-display text-xl font-semibold text-foreground">
          <span className="font-mono text-sm text-muted-foreground">{product.code}</span>
          <span className="truncate">{form.title || t("(bez názvu)")}</span>
          <StatusBadge status={form.active ? "active" : "inactive"} />
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            {t("Aktivní")} <Switch checked={form.active} onCheckedChange={(v) => set("active", v)} />
          </label>
          <RePullDialog productId={productId} onApply={(patch) => setForm((f) => (f ? { ...f, ...patch } : f))} />
          <Button onClick={() => save.mutate(form)} disabled={!dirty || save.isPending}>
            {t("Uložit")}
          </Button>
        </div>
      </div>

      <Tabs defaultValue="obsah" className={cn("gap-4", modal && "min-h-0 flex-1 px-6 pt-4 pb-6")}>
        <TabsList className="flex w-full flex-wrap">
          <TabsTrigger value="obsah">{t("Obsah")}</TabsTrigger>
          <TabsTrigger value="seo">SEO</TabsTrigger>
          <TabsTrigger value="parametry">{t("Parametry")}</TabsTrigger>
          <TabsTrigger value="obrazky">{t("Obrázky")}</TabsTrigger>
          <TabsTrigger value="kategorie">{t("Kategorie")}</TabsTrigger>
          <TabsTrigger value="cena">{t("Cena")}</TabsTrigger>
          <TabsTrigger value="poznamka">{t("Poznámka")}</TabsTrigger>
        </TabsList>

        <div className={modal ? "min-h-0 flex-1 overflow-y-auto pr-1" : undefined}>
          <TabsContent value="obsah">
            <FormSection title={t("Obsah")}>
              <Field label={t("Název")}>
                <Input value={form.title} onChange={(e) => set("title", e.target.value)} />
              </Field>
              <Field label={t("Krátký popis")}>
                <Textarea value={form.short_description} onChange={(e) => set("short_description", e.target.value)} />
              </Field>
              <Field label={t("Dlouhý popis")}>
                <RichTextEditor value={form.long_description} onChange={(v) => set("long_description", v)} />
              </Field>
            </FormSection>
          </TabsContent>

          <TabsContent value="seo">
            <FormSection title="SEO">
              <Field label={t("SEO titulek")}>
                <Input value={form.seo_title} onChange={(e) => set("seo_title", e.target.value)} />
              </Field>
              <Field label={t("SEO popis")}>
                <Textarea value={form.seo_description} onChange={(e) => set("seo_description", e.target.value)} />
              </Field>
              <Field label="URL slug">
                <Input value={form.url_slug} onChange={(e) => set("url_slug", e.target.value)} />
              </Field>
            </FormSection>
          </TabsContent>

          <TabsContent value="parametry">
            <FormSection
              title={t("Parametry")}
              actions={
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    set("params", [...form.params, { name: "", value: "", ord: form.params.length }])
                  }
                >
                  <Plus className="size-4" /> {t("Přidat")}
                </Button>
              }
            >
              {form.params.map((p, i) => (
                <div key={i} className="flex items-center gap-2">
                  <Input
                    className="w-48"
                    placeholder={t("Název")}
                    value={p.name}
                    onChange={(e) =>
                      set("params", form.params.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))
                    }
                  />
                  <Input
                    placeholder={t("Hodnota")}
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
          </TabsContent>

          <TabsContent value="obrazky">
            <FormSection
              title={t("Obrázky")}
              actions={
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => set("images", [...form.images, { url: "", alt: "", ord: form.images.length }])}
                >
                  <Plus className="size-4" /> {t("Přidat")}
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
          </TabsContent>

          <TabsContent value="kategorie">
            <FormSection title={t("Kategorie")}>
              <CategoryChecklist
                categories={categories ?? []}
                value={form.categories}
                onChange={(v) => set("categories", v)}
              />
            </FormSection>
          </TabsContent>

          <TabsContent value="cena">
            <PricingCard
              code={product.code}
              pricePurchase={product.price_purchase}
              coefficient={form.coefficient}
              marginPct={form.margin_pct}
              onChange={(patch) => setForm((f) => (f ? { ...f, ...patch } : f))}
            />
          </TabsContent>

          <TabsContent value="poznamka">
            <FormSection title={t("Poznámka")}>
              <Textarea value={form.note} onChange={(e) => set("note", e.target.value)} />
            </FormSection>
          </TabsContent>
        </div>
      </Tabs>

      {!modal && (
        <UnsavedChangesBar
          dirty={dirty}
          saving={save.isPending}
          onSave={() => save.mutate(form)}
          onDiscard={() => setForm(toForm(product))}
        />
      )}
    </div>
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
  const { t } = useT()
  const byParent = new Map<number | null, Category[]>()
  categories.forEach((c) => {
    const list = byParent.get(c.parent_id) ?? []
    list.push(c)
    byParent.set(c.parent_id, list)
  })

  const render = (parentId: number | null, depth: number, seen: Set<number>): React.ReactNode =>
    (byParent.get(parentId) ?? [])
      .filter((c) => !seen.has(c.id)) // defensive against cyclic category data
      .map((c) => {
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
                {t("hlavní")}
              </label>
            )}
          </div>
          {render(c.id, depth + 1, new Set(seen).add(c.id))}
        </div>
      )
    })

  return <div>{render(null, 0, new Set())}</div>
}
