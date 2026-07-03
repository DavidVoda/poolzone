import { act, renderHook } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"
import { useLocalStorage } from "./use-local-storage"

describe("useLocalStorage", () => {
  beforeEach(() => localStorage.clear())

  it("persists and restores", () => {
    const { result } = renderHook(() => useLocalStorage("cols", { a: true }))
    act(() => result.current[1]({ a: false }))
    expect(JSON.parse(localStorage.getItem("cols")!)).toEqual({ a: false })
    const { result: fresh } = renderHook(() => useLocalStorage("cols", { a: true }))
    expect(fresh.current[0]).toEqual({ a: false })
  })

  it("survives corrupt json", () => {
    localStorage.setItem("cols", "{nope")
    const { result } = renderHook(() => useLocalStorage("cols", { a: true }))
    expect(result.current[0]).toEqual({ a: true })
  })
})
