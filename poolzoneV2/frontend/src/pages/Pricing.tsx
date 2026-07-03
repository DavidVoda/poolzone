import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/app/PageHeader"
import { FormSection } from "@/components/form/FormSection"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { client, unwrap, type Product } from "@/lib/api"
import { formatKc, formatPct } from "@/lib/format"

export default function Pricing() {
  return (
    <>
      <PageHeader title="Ceny" />
      <div className="space-y-5">
        <MarginDefaultsCard />
        <OverridesTable />
      </div>
    </>
  )
}

function MarginDefaultsCard() {
  const queryClient = useQueryClient()
  const { data: rules } = useQuery({
    queryKey: ["pricing-rules-raw"],
    queryFn: () => unwrap(client.GET("/api/pricing/rules")),
  })
  const [edits, setEdits] = useState<Record<number, string>>({})

  const save = useMutation({
    mutationFn: ({ id, margin_pct }: { id: number; margin_pct: string }) =>
      unwrap(client.PUT("/api/pricing/rules/{rule_id}", { params: { path: { rule_id: id } }, body: { margin_pct } })),
    onSuccess: () => {
      toast.success("Marže uložena")
      setEdits({})
      queryClient.invalidateQueries({ queryKey: ["pricing-rules-raw"] })
      queryClient.invalidateQueries({ queryKey: ["pricing-rules"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <FormSection title="Výchozí marže">
      {rules?.map((r) => (
        <div key={r.id} className="flex items-center gap-3 text-sm">
          <span className="w-48">{r.scope === "default" ? "Globální výchozí" : `Prefix „${r.match_value}“`}</span>
          <Input
            className="w-28"
            value={edits[r.id] ?? r.margin_pct}
            onChange={(e) => setEdits((x) => ({ ...x, [r.id]: e.target.value }))}
          />
          <span className="text-muted-foreground">{formatPct(edits[r.id] ?? r.margin_pct)}</span>
          {edits[r.id] !== undefined && edits[r.id] !== r.margin_pct && (
            <Button size="sm" onClick={() => save.mutate({ id: r.id, margin_pct: edits[r.id] })}>
              Uložit
            </Button>
          )}
        </div>
      ))}
    </FormSection>
  )
}

function OverridesTable() {
  const queryClient = useQueryClient()
  const { data } = useQuery({
    queryKey: ["products", "overrides"],
    queryFn: () =>
      unwrap(client.GET("/api/products", { params: { query: { overrides: true, limit: 500 } } })),
  })
  const [edits, setEdits] = useState<Record<number, { coefficient?: string; margin_pct?: string | null }>>({})

  const save = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: { coefficient?: string; margin_pct?: string | null } }) =>
      unwrap(client.PATCH("/api/products/{product_id}", { params: { path: { product_id: id } }, body: patch })),
    onSuccess: (_, { id }) => {
      toast.success("Uloženo")
      setEdits((e) => {
        const next = { ...e }
        delete next[id]
        return next
      })
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const rows: Product[] = data?.items ?? []

  return (
    <FormSection title={`Produkty s vlastní cenotvorbou (${data?.total ?? 0})`}>
      <Table>
        <TableHeader>
          <TableRow className="bg-sky-50/60 hover:bg-sky-50/60">
            <TableHead className="text-sky-800">Kód</TableHead>
            <TableHead className="text-sky-800">Název</TableHead>
            <TableHead className="text-sky-800">Nákup</TableHead>
            <TableHead className="text-sky-800">Koeficient</TableHead>
            <TableHead className="text-sky-800">Marže</TableHead>
            <TableHead className="text-sky-800">Prodej</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((p) => {
            const e = edits[p.id]
            return (
              <TableRow key={p.id}>
                <TableCell className="font-mono text-xs">{p.code}</TableCell>
                <TableCell className="max-w-md truncate">{p.title}</TableCell>
                <TableCell>{formatKc(p.price_purchase)}</TableCell>
                <TableCell>
                  <Input
                    className="w-24"
                    value={e?.coefficient ?? p.coefficient}
                    onChange={(ev) =>
                      setEdits((x) => ({ ...x, [p.id]: { ...x[p.id], coefficient: ev.target.value } }))
                    }
                  />
                </TableCell>
                <TableCell>
                  <Input
                    className="w-24"
                    placeholder="výchozí"
                    value={e?.margin_pct !== undefined ? (e.margin_pct ?? "") : (p.margin_pct ?? "")}
                    onChange={(ev) =>
                      setEdits((x) => ({
                        ...x,
                        [p.id]: { ...x[p.id], margin_pct: ev.target.value === "" ? null : ev.target.value },
                      }))
                    }
                  />
                </TableCell>
                <TableCell className="font-medium">{formatKc(p.sale_price)}</TableCell>
                <TableCell>
                  {e && (
                    <Button size="sm" onClick={() => save.mutate({ id: p.id, patch: e })}>
                      Uložit
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </FormSection>
  )
}
