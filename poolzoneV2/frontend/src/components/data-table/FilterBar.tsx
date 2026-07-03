import { useRef, useState } from "react"
import { Plus, Search, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  OP_LABELS,
  OPS_BY_TYPE,
  type Filter,
  type FilterableColumn,
  type FilterOp,
} from "@/lib/filters"

type Props = {
  columns: FilterableColumn[]
  filters: Filter[]
  onChange: (filters: Filter[]) => void
  q: string
  onQChange: (q: string) => void
  children?: React.ReactNode // right-aligned extras (counts)
}

const NEEDS_VALUE = (op: FilterOp) => op !== "empty" && op !== "notempty"

function chipLabel(f: Filter, columns: FilterableColumn[]) {
  const col = columns.find((c) => c.id === f.col)
  const value =
    col?.type === "select"
      ? (col.options?.find((o) => o.value === f.value)?.label ?? f.value)
      : col?.type === "bool"
        ? (f.value === "true" ? "ano" : "ne")
        : f.value
  return `${col?.label ?? f.col} ${OP_LABELS[f.op]} ${NEEDS_VALUE(f.op) ? value : ""}`.trim()
}

export function FilterBar({ columns, filters, onChange, q, onQChange, children }: Props) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Partial<Filter>>({})
  const draftCol = columns.find((c) => c.id === draft.col)
  const qTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const commit = () => {
    if (!draft.col || !draft.op) return
    if (NEEDS_VALUE(draft.op) && !draft.value && draftCol?.type !== "bool") return
    onChange([...filters, { col: draft.col, op: draft.op, value: draft.value ?? "" } as Filter])
    setDraft({})
    setOpen(false)
  }

  return (
    <div className="mb-3 flex flex-wrap items-center gap-2">
      <div className="relative">
        <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
        <Input
          className="w-64 pl-8"
          placeholder="Hledat kód / název / EAN…"
          defaultValue={q}
          onChange={(e) => {
            const v = e.target.value
            clearTimeout(qTimer.current)
            qTimer.current = setTimeout(() => onQChange(v), 300)
          }}
        />
      </div>

      {filters.map((f, i) => (
        <button
          key={i}
          onClick={() => onChange(filters.filter((_, j) => j !== i))}
          className="flex items-center gap-1 rounded-full bg-accent px-3 py-1 text-sm text-accent-foreground hover:opacity-80"
        >
          {chipLabel(f, columns)} <X className="size-3" />
        </button>
      ))}

      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" size="sm" className="rounded-full border-dashed">
            <Plus className="size-4" /> Filtr
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-64 space-y-2" align="start">
          <Select value={draft.col ?? ""} onValueChange={(col) => setDraft({ col })}>
            <SelectTrigger>
              <SelectValue placeholder="Sloupec" />
            </SelectTrigger>
            <SelectContent>
              {columns.map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {draftCol && (
            <Select value={draft.op ?? ""} onValueChange={(op) => setDraft({ ...draft, op: op as FilterOp })}>
              <SelectTrigger>
                <SelectValue placeholder="Podmínka" />
              </SelectTrigger>
              <SelectContent>
                {OPS_BY_TYPE[draftCol.type].map((op) => (
                  <SelectItem key={op} value={op}>
                    {OP_LABELS[op]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          {draft.op && NEEDS_VALUE(draft.op) && draftCol?.type === "select" && (
            <Select value={draft.value ?? ""} onValueChange={(value) => setDraft({ ...draft, value })}>
              <SelectTrigger>
                <SelectValue placeholder="Hodnota" />
              </SelectTrigger>
              <SelectContent>
                {draftCol.options?.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {draft.op && NEEDS_VALUE(draft.op) && draftCol?.type === "bool" && (
            <Select value={draft.value ?? ""} onValueChange={(value) => setDraft({ ...draft, value })}>
              <SelectTrigger>
                <SelectValue placeholder="Hodnota" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">ano</SelectItem>
                <SelectItem value="false">ne</SelectItem>
              </SelectContent>
            </Select>
          )}
          {draft.op && NEEDS_VALUE(draft.op) && draftCol && draftCol.type !== "select" && draftCol.type !== "bool" && (
            <Input
              placeholder="Hodnota"
              value={draft.value ?? ""}
              onChange={(e) => setDraft({ ...draft, value: e.target.value })}
              onKeyDown={(e) => e.key === "Enter" && commit()}
            />
          )}

          <Button size="sm" className="w-full" onClick={commit}>
            Přidat filtr
          </Button>
        </PopoverContent>
      </Popover>

      <div className="ml-auto flex items-center gap-2">{children}</div>
    </div>
  )
}
