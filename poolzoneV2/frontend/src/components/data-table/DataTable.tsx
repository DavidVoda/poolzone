import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type RowSelectionState,
  type VisibilityState,
} from "@tanstack/react-table"
import { ArrowDown, ArrowUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useLocalStorage } from "@/lib/use-local-storage"
import { cn } from "@/lib/utils"
import { ColumnMenu } from "./ColumnMenu"

const PAGE_SIZE = 50

type Props<T> = {
  columns: ColumnDef<T, unknown>[]
  data: T[]
  total: number
  isLoading?: boolean
  /** '[-]col' server sort, as in the URL */
  sort: string | null
  onSortChange: (sort: string | null) => void
  page: number // 0-based
  onPageChange: (page: number) => void
  onRowClick?: (row: T) => void
  rowSelection?: RowSelectionState
  onRowSelectionChange?: (s: RowSelectionState) => void
  getRowId?: (row: T) => string
  storageKey: string // localStorage key for column visibility
  stickyCount?: number // first N columns stick on horizontal scroll
  rowClassName?: (row: T) => string | undefined
}

export function DataTable<T>({
  columns,
  data,
  total,
  isLoading,
  sort,
  onSortChange,
  page,
  onPageChange,
  onRowClick,
  rowSelection,
  onRowSelectionChange,
  getRowId,
  storageKey,
  stickyCount = 0,
  rowClassName,
}: Props<T>) {
  const [visibility, setVisibility] = useLocalStorage<VisibilityState>(storageKey, {})

  const table = useReactTable({
    data,
    columns,
    state: { columnVisibility: visibility, rowSelection: rowSelection ?? {} },
    onColumnVisibilityChange: (u) => setVisibility(typeof u === "function" ? u(visibility) : u),
    onRowSelectionChange: (u) =>
      onRowSelectionChange?.(typeof u === "function" ? u(rowSelection ?? {}) : u),
    getRowId,
    getCoreRowModel: getCoreRowModel(),
    manualSorting: true,
    manualPagination: true,
    enableRowSelection: !!onRowSelectionChange,
  })

  const cycleSort = (id: string) =>
    onSortChange(sort === id ? `-${id}` : sort === `-${id}` ? null : id)

  const sticky = (i: number) =>
    i < stickyCount ? cn("sticky bg-background z-10", i === 0 ? "left-0" : "left-32") : undefined

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id} className="bg-sky-50/60 hover:bg-sky-50/60">
                {hg.headers.map((h, i) => {
                  const id = h.column.id
                  const sortable = h.column.columnDef.enableSorting !== false
                  return (
                    <TableHead
                      key={h.id}
                      className={cn("whitespace-nowrap text-sky-800", sticky(i), i === 0 && "w-32 min-w-32")}
                    >
                      {sortable ? (
                        <button className="flex items-center gap-1" onClick={() => cycleSort(id)}>
                          {flexRender(h.column.columnDef.header, h.getContext())}
                          {sort === id && <ArrowUp className="size-3" />}
                          {sort === `-${id}` && <ArrowDown className="size-3" />}
                        </button>
                      ) : (
                        flexRender(h.column.columnDef.header, h.getContext())
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  Načítám…
                </TableCell>
              </TableRow>
            ) : data.length === 0 ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center text-muted-foreground">
                  Žádné výsledky.
                </TableCell>
              </TableRow>
            ) : (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() ? "selected" : undefined}
                  className={cn(onRowClick && "cursor-pointer", rowClassName?.(row.original))}
                  onClick={() => onRowClick?.(row.original)}
                >
                  {row.getVisibleCells().map((cell, i) => (
                    <TableCell key={cell.id} className={cn("whitespace-nowrap", sticky(i))}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
      <div className="flex items-center justify-between border-t px-3 py-2 text-sm text-muted-foreground">
        <div className="flex items-center gap-3">
          <ColumnMenu table={table} />
          <span>{total.toLocaleString("cs-CZ")} položek</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={page === 0} onClick={() => onPageChange(page - 1)}>
            Předchozí
          </Button>
          <span>
            {page + 1} / {pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page + 1 >= pages}
            onClick={() => onPageChange(page + 1)}
          >
            Další
          </Button>
        </div>
      </div>
    </div>
  )
}

export { PAGE_SIZE }
