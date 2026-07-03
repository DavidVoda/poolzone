import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import type { ColumnDef, RowSelectionState } from "@tanstack/react-table"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { PageHeader } from "@/components/app/PageHeader"
import { StatusBadge } from "@/components/app/StatusBadge"
import { DataTable, PAGE_SIZE } from "@/components/data-table/DataTable"
import { FilterBar } from "@/components/data-table/FilterBar"
import { ProductPeekPanel } from "@/components/app/ProductPeekPanel"
import { client, unwrap, type Product } from "@/lib/api"
import { filterToParam, type FilterableColumn } from "@/lib/filters"
import { formatKc, formatPct } from "@/lib/format"
import { useTableParams } from "@/lib/use-table-params"

export default function Products() {
  const { filters, q, sort, page, peek, setFilters, setQ, setSort, setPage, setPeek } = useTableParams()
  const [selection, setSelection] = useState<RowSelectionState>({})
  const queryClient = useQueryClient()

  const { data: suppliers } = useQuery({
    queryKey: ["suppliers"],
    queryFn: () => unwrap(client.GET("/api/suppliers")),
  })
  const supplierName = (id: number | null) => suppliers?.find((s) => s.id === id)?.name ?? "—"

  const query = useQuery({
    queryKey: ["products", { q, filters, sort, page }],
    queryFn: () =>
      unwrap(
        client.GET("/api/products", {
          params: {
            query: {
              q: q || undefined,
              filter: filters.map(filterToParam),
              sort: sort ?? undefined,
              limit: PAGE_SIZE,
              offset: page * PAGE_SIZE,
            },
          },
        }),
      ),
  })

  const bulkActive = useMutation({
    mutationFn: async (active: boolean) => {
      for (const id of Object.keys(selection)) {
        await unwrap(
          client.PATCH("/api/products/{product_id}", {
            params: { path: { product_id: Number(id) } },
            body: { active },
          }),
        )
      }
    },
    onSuccess: (_, active) => {
      toast.success(active ? "Produkty aktivovány" : "Produkty deaktivovány")
      setSelection({})
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const filterable: FilterableColumn[] = useMemo(
    () => [
      { id: "code", label: "Kód", type: "text" },
      { id: "title", label: "Název", type: "text" },
      { id: "ean", label: "EAN", type: "text" },
      { id: "manufacturer", label: "Výrobce", type: "text" },
      {
        id: "supplier_id",
        label: "Dodavatel",
        type: "select",
        options: (suppliers ?? []).map((s) => ({ value: String(s.id), label: s.name })),
      },
      { id: "stock", label: "Sklad", type: "number" },
      { id: "availability", label: "Dostupnost", type: "text" },
      { id: "active", label: "Aktivní", type: "bool" },
      { id: "price_purchase", label: "Nákupní cena", type: "number" },
      { id: "coefficient", label: "Koeficient", type: "number" },
      { id: "margin_pct", label: "Marže", type: "number" },
      { id: "long_description", label: "Dlouhý popis", type: "text" },
      { id: "seo_title", label: "SEO titulek", type: "text" },
    ],
    [suppliers],
  )

  const columns: ColumnDef<Product, unknown>[] = useMemo(
    () => [
      {
        id: "select",
        enableSorting: false,
        enableHiding: false,
        header: () => null,
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(v) => row.toggleSelected(!!v)}
            onClick={(e) => e.stopPropagation()}
          />
        ),
      },
      { accessorKey: "code", id: "code", header: "Kód", meta: { label: "Kód" }, enableHiding: false },
      { accessorKey: "title", id: "title", header: "Název", meta: { label: "Název" }, enableHiding: false },
      {
        id: "supplier_id",
        header: "Dodavatel",
        meta: { label: "Dodavatel" },
        cell: ({ row }) => supplierName(row.original.supplier_id),
      },
      { accessorKey: "manufacturer", id: "manufacturer", header: "Výrobce", meta: { label: "Výrobce" } },
      { accessorKey: "ean", id: "ean", header: "EAN", meta: { label: "EAN" } },
      { accessorKey: "stock", id: "stock", header: "Sklad", meta: { label: "Sklad" } },
      { accessorKey: "availability", id: "availability", header: "Dostupnost", meta: { label: "Dostupnost" } },
      {
        id: "price_purchase",
        header: "Nákup",
        meta: { label: "Nákupní cena" },
        cell: ({ row }) => formatKc(row.original.price_purchase),
      },
      {
        accessorKey: "coefficient",
        id: "coefficient",
        header: "Koef.",
        meta: { label: "Koeficient" },
      },
      {
        id: "margin_pct",
        header: "Marže",
        meta: { label: "Marže" },
        cell: ({ row }) => formatPct(row.original.margin_pct),
      },
      {
        id: "sale_price",
        enableSorting: false,
        header: "Prodej",
        meta: { label: "Prodejní cena" },
        cell: ({ row }) => <span className="font-medium">{formatKc(row.original.sale_price)}</span>,
      },
      {
        id: "active",
        header: "Stav",
        meta: { label: "Stav" },
        cell: ({ row }) => <StatusBadge status={row.original.active ? "active" : "inactive"} />,
      },
    ],
    [suppliers],
  )

  const selectedCount = Object.keys(selection).length

  return (
    <>
      <PageHeader
        title="Produkty"
        actions={
          selectedCount > 0 && (
            <>
              <span className="text-sm text-muted-foreground">{selectedCount} vybráno</span>
              <Button size="sm" variant="outline" onClick={() => bulkActive.mutate(true)}>
                Aktivovat
              </Button>
              <Button size="sm" variant="outline" onClick={() => bulkActive.mutate(false)}>
                Deaktivovat
              </Button>
            </>
          )
        }
      />
      <FilterBar columns={filterable} filters={filters} onChange={setFilters} q={q} onQChange={setQ} />
      <DataTable
        columns={columns}
        data={query.data?.items ?? []}
        total={query.data?.total ?? 0}
        isLoading={query.isLoading}
        sort={sort}
        onSortChange={setSort}
        page={page}
        onPageChange={setPage}
        onRowClick={(p) => setPeek(String(p.id))}
        rowSelection={selection}
        onRowSelectionChange={setSelection}
        getRowId={(p) => String(p.id)}
        storageKey="products-columns"
        stickyCount={0}
        rowClassName={(p) => (String(p.id) === peek ? "bg-accent/40" : undefined)}
      />
      {peek && (
        <ProductPeekPanel
          productId={Number(peek)}
          productIds={(query.data?.items ?? []).map((p) => p.id)}
          onNavigate={(id) => setPeek(String(id))}
          onClose={() => setPeek(null)}
        />
      )}
    </>
  )
}
