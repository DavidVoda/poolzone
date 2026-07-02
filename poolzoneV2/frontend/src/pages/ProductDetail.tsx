import { useEffect, useState, type ReactNode } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Link, useParams } from "react-router-dom"
import { api, type Product, type ProductUpdate } from "@/lib/api"
import { Button, Card, Input } from "@/components/ui"

function field(p: Product): ProductUpdate {
  return {
    title: p.title,
    long_description: p.long_description,
    url_slug: p.url_slug,
    active: p.active,
    coefficient: p.coefficient,
    margin_pct: p.margin_pct,
    note: p.note,
  }
}

export default function ProductDetail() {
  const { id } = useParams()
  const pid = Number(id)
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ["product", pid],
    // The list endpoint is the only read; find our row in it. ponytail: add a
    // single-product GET to the client when a product is deep-linked cold.
    queryFn: async () => (await api.listProducts()).find((p) => p.id === pid) ?? null,
  })
  const [form, setForm] = useState<ProductUpdate>({})
  useEffect(() => {
    if (data) setForm(field(data))
  }, [data])

  const save = useMutation({
    mutationFn: () => api.updateProduct(pid, form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["products"] })
      qc.invalidateQueries({ queryKey: ["product", pid] })
    },
  })

  if (!data) return <p className="text-slate-400">Loading…</p>

  const set = (k: keyof ProductUpdate) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [k]: e.target.value }))

  return (
    <div className="space-y-4">
      <Link to="/" className="text-sm text-blue-600 hover:underline">
        ← Products
      </Link>
      <h1 className="font-mono text-lg text-slate-900">{data.code}</h1>
      <Card className="max-w-2xl space-y-4 p-6">
        <Labeled label="Title">
          <Input value={form.title ?? ""} onChange={set("title")} />
        </Labeled>
        <Labeled label="Long description">
          <textarea
            className="min-h-24 w-full rounded-md border border-slate-300 p-2 text-sm outline-none focus:border-slate-500"
            value={form.long_description ?? ""}
            onChange={set("long_description")}
          />
        </Labeled>
        <Labeled label="URL slug">
          <Input value={form.url_slug ?? ""} onChange={set("url_slug")} />
        </Labeled>
        <div className="grid grid-cols-2 gap-4">
          <Labeled label="Coefficient">
            <Input value={form.coefficient ?? ""} onChange={set("coefficient")} />
          </Labeled>
          <Labeled label="Margin % (blank = use rule)">
            <Input value={form.margin_pct ?? ""} onChange={set("margin_pct")} />
          </Labeled>
        </div>
        <Labeled label="Note">
          <Input value={form.note ?? ""} onChange={set("note")} />
        </Labeled>
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.active ?? false}
            onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))}
          />
          Active
        </label>
        <div className="flex items-center gap-3">
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            {save.isPending ? "Saving…" : "Save"}
          </Button>
          {save.isSuccess && <span className="text-sm text-green-600">Saved</span>}
          {save.isError && <span className="text-sm text-red-600">Error</span>}
        </div>
      </Card>
    </div>
  )
}

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-1">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      {children}
    </div>
  )
}
