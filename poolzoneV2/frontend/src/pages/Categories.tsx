import { useEffect, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/app/PageHeader"
import { TreeView } from "@/components/app/TreeView"
import { Field } from "@/components/form/Field"
import { FormSection } from "@/components/form/FormSection"
import { client, unwrap, type Category } from "@/lib/api"

export default function Categories() {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<number | null>(null)

  const { data: categories } = useQuery({
    queryKey: ["categories"],
    queryFn: () => unwrap(client.GET("/api/categories")),
  })
  const selected = categories?.find((c) => c.id === selectedId) ?? null

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["categories"] })

  const create = useMutation({
    mutationFn: (parent_id: number | null) =>
      unwrap(client.POST("/api/categories", { body: { name: "Nová kategorie", parent_id } })),
    onSuccess: (c) => {
      invalidate()
      setSelectedId(c.id)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const remove = useMutation({
    mutationFn: (id: number) =>
      unwrap(client.DELETE("/api/categories/{category_id}", { params: { path: { category_id: id } } })),
    onSuccess: () => {
      invalidate()
      setSelectedId(null)
      toast.success("Kategorie smazána")
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <>
      <PageHeader
        title="Kategorie"
        actions={
          <Button size="sm" onClick={() => create.mutate(selectedId)}>
            <Plus className="size-4" /> Přidat {selected ? `do „${selected.name}“` : "kořenovou"}
          </Button>
        }
      />
      <div className="flex items-start gap-5">
        <div className="w-80 shrink-0 rounded-lg border bg-card p-2 shadow-sm">
          {categories && <TreeView nodes={categories} selectedId={selectedId} onSelect={setSelectedId} />}
        </div>
        <div className="min-w-0 flex-1 space-y-5">
          {selected ? (
            <>
              <CategoryForm
                key={selected.id}
                category={selected}
                categories={categories ?? []}
                onSaved={invalidate}
                onDelete={() => {
                  if (window.confirm(`Smazat kategorii „${selected.name}“?`)) remove.mutate(selected.id)
                }}
              />
              <MappingsTable categoryId={selected.id} categories={categories ?? []} />
            </>
          ) : (
            <p className="text-muted-foreground">Vyberte kategorii vlevo.</p>
          )}
        </div>
      </div>
    </>
  )
}

function CategoryForm({
  category,
  categories,
  onSaved,
  onDelete,
}: {
  category: Category
  categories: Category[]
  onSaved: () => void
  onDelete: () => void
}) {
  const [form, setForm] = useState({
    name: category.name,
    parent_id: category.parent_id,
    seo_title: category.seo_title ?? "",
    seo_description: category.seo_description ?? "",
  })
  useEffect(
    () =>
      setForm({
        name: category.name,
        parent_id: category.parent_id,
        seo_title: category.seo_title ?? "",
        seo_description: category.seo_description ?? "",
      }),
    [category],
  )

  const save = useMutation({
    mutationFn: () =>
      unwrap(
        client.PATCH("/api/categories/{category_id}", {
          params: { path: { category_id: category.id } },
          body: {
            name: form.name,
            parent_id: form.parent_id,
            seo_title: form.seo_title || null,
            seo_description: form.seo_description || null,
          },
        }),
      ),
    onSuccess: () => {
      toast.success("Uloženo")
      onSaved()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  // A category can't be its own parent or a descendant's (would create a cycle).
  const descendants = new Set<number>([category.id])
  let grew = true
  while (grew) {
    grew = false
    for (const c of categories) {
      if (c.parent_id != null && descendants.has(c.parent_id) && !descendants.has(c.id)) {
        descendants.add(c.id)
        grew = true
      }
    }
  }
  const parentOptions = categories.filter((c) => !descendants.has(c.id))

  return (
    <FormSection
      title={`Kategorie: ${category.name}`}
      actions={
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" onClick={onDelete}>
            <Trash2 className="size-4 text-red-500" />
          </Button>
          <Button size="sm" onClick={() => save.mutate()} disabled={save.isPending}>
            Uložit
          </Button>
        </div>
      }
    >
      <Field label="Název">
        <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </Field>
      <Field label="Nadřazená kategorie">
        <Select
          value={form.parent_id === null ? "root" : String(form.parent_id)}
          onValueChange={(v) => setForm({ ...form, parent_id: v === "root" ? null : Number(v) })}
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="root">(kořen)</SelectItem>
            {parentOptions.map((c) => (
              <SelectItem key={c.id} value={String(c.id)}>
                {c.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <Field label="SEO titulek">
        <Input value={form.seo_title} onChange={(e) => setForm({ ...form, seo_title: e.target.value })} />
      </Field>
      <Field label="SEO popis">
        <Textarea
          value={form.seo_description}
          onChange={(e) => setForm({ ...form, seo_description: e.target.value })}
        />
      </Field>
    </FormSection>
  )
}

function MappingsTable({ categoryId, categories }: { categoryId: number; categories: Category[] }) {
  const queryClient = useQueryClient()
  const { data: mappings } = useQuery({
    queryKey: ["mappings", categoryId],
    queryFn: () =>
      unwrap(client.GET("/api/categories/mappings", { params: { query: { category_id: categoryId } } })),
  })

  const reassign = useMutation({
    mutationFn: ({ id, category_id }: { id: number; category_id: number }) =>
      unwrap(
        client.PATCH("/api/categories/mappings/{mapping_id}", {
          params: { path: { mapping_id: id } },
          body: { category_id },
        }),
      ),
    onSuccess: () => {
      toast.success("Mapování přesunuto")
      queryClient.invalidateQueries({ queryKey: ["mappings"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <FormSection title="Mapování dodavatelských kategorií">
      {!mappings?.length && <p className="text-sm text-muted-foreground">Žádná mapování na tuto kategorii.</p>}
      {mappings?.map((m) => (
        <div key={m.id} className="flex items-center gap-3 text-sm">
          <span className="min-w-0 flex-1 truncate font-mono text-xs">{m.supplier_path}</span>
          <Select
            value={String(m.category_id)}
            onValueChange={(v) => reassign.mutate({ id: m.id, category_id: Number(v) })}
          >
            <SelectTrigger className="w-56">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {categories.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      ))}
    </FormSection>
  )
}
