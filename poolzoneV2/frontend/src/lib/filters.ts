export const FILTER_OPS = ["eq", "ne", "gt", "lt", "contains", "empty", "notempty"] as const
export type FilterOp = (typeof FILTER_OPS)[number]
export type Filter = { col: string; op: FilterOp; value: string }

export const OP_LABELS: Record<FilterOp, string> = {
  eq: "=",
  ne: "≠",
  gt: ">",
  lt: "<",
  contains: "obsahuje",
  empty: "prázdné",
  notempty: "vyplněné",
}

export type ColumnType = "text" | "number" | "bool" | "select"

export const OPS_BY_TYPE: Record<ColumnType, FilterOp[]> = {
  text: ["contains", "eq", "ne", "empty", "notempty"],
  number: ["eq", "ne", "gt", "lt", "empty", "notempty"],
  bool: ["eq"],
  select: ["eq", "ne"],
}

export type FilterableColumn = {
  id: string
  label: string
  type: ColumnType
  options?: { value: string; label: string }[] // for type "select"
}

export const filterToParam = (f: Filter) => `${f.col}:${f.op}:${f.value}`

export function filterFromParam(s: string): Filter | null {
  const [col, op, ...rest] = s.split(":")
  if (!col || !FILTER_OPS.includes(op as FilterOp)) return null
  return { col, op: op as FilterOp, value: rest.join(":") }
}
