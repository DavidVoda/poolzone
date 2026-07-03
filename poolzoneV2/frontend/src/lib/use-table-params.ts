import { useSearchParams } from "react-router-dom"
import { filterFromParam, filterToParam, type Filter } from "./filters"

export function useTableParams() {
  const [params, setParams] = useSearchParams()

  const filters = params.getAll("filter").map(filterFromParam).filter((f): f is Filter => f !== null)
  const q = params.get("q") ?? ""
  const sort = params.get("sort")
  const page = Number(params.get("page") ?? "0")
  const peek = params.get("peek")

  const update = (fn: (p: URLSearchParams) => void) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev)
        fn(next)
        return next
      },
      { replace: true },
    )

  return {
    filters,
    q,
    sort,
    page,
    peek,
    setFilters: (fs: Filter[]) =>
      update((p) => {
        p.delete("filter")
        fs.forEach((f) => p.append("filter", filterToParam(f)))
        p.delete("page")
      }),
    setQ: (v: string) =>
      update((p) => {
        v ? p.set("q", v) : p.delete("q")
        p.delete("page")
      }),
    setSort: (v: string | null) => update((p) => (v ? p.set("sort", v) : p.delete("sort"))),
    setPage: (n: number) => update((p) => (n > 0 ? p.set("page", String(n)) : p.delete("page"))),
    setPeek: (id: string | null) => update((p) => (id ? p.set("peek", id) : p.delete("peek"))),
  }
}
