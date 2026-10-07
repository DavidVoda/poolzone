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
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { ProductDetailForm } from "@/components/app/ProductDetailForm"
import { client, unwrap, type Product } from "@/lib/api"
import { filterToParam, type FilterableColumn } from "@/lib/filters"
import { formatKc, formatPct } from "@/lib/format"
import { useT } from "@/lib/i18n"
import { useTableParams } from "@/lib/use-table-params"

export default function Products() {
  const { t } = useT()
  const { filters, q, sort, page, peek, setFilters, setQ, setSort, setPage, setPeek } = useTableParams()
  const [selection, setSelection] = useState<RowSelectionState>({})
  const [peekDirty, setPeekDirty] = useState(false)
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
    mutationFn: (active: boolean) =>
      Promise.all(
        Object.keys(selection).map((id) =>
          unwrap(
            client.PATCH("/api/products/{product_id}", {
              params: { path: { product_id: Number(id) } },
              body: { active },
            }),
          ),
        ),
      ),
    onSuccess: (_, active) => {
      toast.success(active ? t("Produkty aktivovány") : t("Produkty deaktivovány"))
      setSelection({})
      queryClient.invalidateQueries({ queryKey: ["products"] })
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const filterable: FilterableColumn[] = useMemo(
    () => [
      { id: "code", label: t("Kód"), type: "text" },
      { id: "title", label: t("Název"), type: "text" },
      { id: "ean", label: "EAN", type: "text" },
      { id: "manufacturer", label: t("Výrobce"), type: "text" },
      {
        id: "supplier_id",
        label: t("Dodavatel"),
        type: "select",
        options: (suppliers ?? []).map((s) => ({ value: String(s.id), label: s.name })),
      },
      { id: "stock", label: t("Sklad"), type: "number" },
      { id: "availability", label: t("Dostupnost"), type: "text" },
      { id: "active", label: t("Aktivní"), type: "bool" },
      { id: "price_purchase", label: t("Nákupní cena"), type: "number" },
      { id: "coefficient", label: t("Koeficient"), type: "number" },
      { id: "margin_pct", label: t("Marže"), type: "number" },
      { id: "long_description", label: t("Dlouhý popis"), type: "text" },
      { id: "seo_title", label: t("SEO titulek"), type: "text" },
    ],
    [suppliers, t],
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
      { accessorKey: "code", id: "code", header: t("Kód"), meta: { label: t("Kód") }, enableHiding: false },
      { accessorKey: "title", id: "title", header: t("Název"), meta: { label: t("Název") }, enableHiding: false },
      {
        id: "supplier_id",
        header: t("Dodavatel"),
        meta: { label: t("Dodavatel") },
        cell: ({ row }) => supplierName(row.original.supplier_id),
      },
      { accessorKey: "manufacturer", id: "manufacturer", header: t("Výrobce"), meta: { label: t("Výrobce") } },
      { accessorKey: "ean", id: "ean", header: "EAN", meta: { label: "EAN" } },
      { accessorKey: "stock", id: "stock", header: t("Sklad"), meta: { label: t("Sklad") } },
      { accessorKey: "availability", id: "availability", header: t("Dostupnost"), meta: { label: t("Dostupnost") } },
      {
        id: "price_purchase",
        header: t("Nákup"),
        meta: { label: t("Nákupní cena") },
        cell: ({ row }) => formatKc(row.original.price_purchase),
      },
      {
        accessorKey: "coefficient",
        id: "coefficient",
        header: t("Koef."),
        meta: { label: t("Koeficient") },
      },
      {
        id: "margin_pct",
        header: t("Marže"),
        meta: { label: t("Marže") },
        cell: ({ row }) => formatPct(row.original.margin_pct),
      },
      {
        id: "sale_price",
        enableSorting: false,
        header: t("Prodej"),
        meta: { label: t("Prodejní cena") },
        cell: ({ row }) => <span className="font-medium">{formatKc(row.original.sale_price)}</span>,
      },
      {
        id: "active",
        header: t("Stav"),
        meta: { label: t("Stav") },
        cell: ({ row }) => <StatusBadge status={row.original.active ? "active" : "inactive"} />,
      },
    ],
    [suppliers, t],
  )

  const selectedCount = Object.keys(selection).length

  return (
    <>
      <PageHeader
        title={t("Produkty")}
        actions={
          selectedCount > 0 && (
            <>
              <span className="text-sm text-muted-foreground">
                {selectedCount} {t("vybráno")}
              </span>
              <Button size="sm" variant="outline" onClick={() => bulkActive.mutate(true)}>
                {t("Aktivovat")}
              </Button>
              <Button size="sm" variant="outline" onClick={() => bulkActive.mutate(false)}>
                {t("Deaktivovat")}
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
      <Dialog
        open={!!peek}
        onOpenChange={(open) => {
          if (open) return
          if (peekDirty && !window.confirm(t("Máte neuložené změny. Opustit stránku?"))) return
          setPeekDirty(false)
          setPeek(null)
        }}
      >
        <DialogContent className="flex h-[85vh] max-h-[880px] w-[1060px] max-w-[92vw] flex-col gap-0 overflow-hidden p-0 sm:max-w-[92vw]">
          <DialogTitle className="sr-only">{t("Produkty")}</DialogTitle>
          {peek && (
            <ProductDetailForm productId={Number(peek)} variant="modal" onDirtyChange={setPeekDirty} />
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
