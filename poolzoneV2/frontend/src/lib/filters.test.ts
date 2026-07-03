import { describe, expect, it } from "vitest"
import { filterFromParam, filterToParam } from "./filters"

describe("filter param serialization", () => {
  it("round-trips a value filter", () => {
    const f = { col: "stock", op: "gt" as const, value: "0" }
    expect(filterToParam(f)).toBe("stock:gt:0")
    expect(filterFromParam("stock:gt:0")).toEqual(f)
  })
  it("keeps colons inside the value", () => {
    expect(filterFromParam("title:contains:8 m3:h")).toEqual({ col: "title", op: "contains", value: "8 m3:h" })
  })
  it("empty ops serialize with trailing colon", () => {
    expect(filterToParam({ col: "margin_pct", op: "empty", value: "" })).toBe("margin_pct:empty:")
    expect(filterFromParam("margin_pct:empty:")).toEqual({ col: "margin_pct", op: "empty", value: "" })
  })
  it("rejects unknown op", () => {
    expect(filterFromParam("stock:wat:1")).toBeNull()
  })
})
