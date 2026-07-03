import { describe, expect, it } from "vitest"
import { resolveMargin, salePrice } from "./pricing"

const RULES = { default: 0.35, AK: 0.34 }

describe("pricing mirror of app/pricing.py", () => {
  it("explicit margin wins", () => {
    expect(resolveMargin({ code: "AK1", margin_pct: "0.45" }, RULES).margin).toBe(0.45)
    expect(resolveMargin({ code: "AK1", margin_pct: "0.45" }, RULES).source).toBe("override")
  })
  it("AK prefix falls to AK rule", () => {
    expect(resolveMargin({ code: "AK1", margin_pct: null }, RULES)).toEqual({ margin: 0.34, source: "prefix", prefix: "AK" })
  })
  it("non-AK falls to default", () => {
    expect(resolveMargin({ code: "ESPA1", margin_pct: null }, RULES)).toEqual({ margin: 0.35, source: "default" })
  })
  it("77 / 0.65 = 118.46", () => {
    expect(salePrice({ code: "ESPA1", price_purchase: "77", coefficient: "1.0", margin_pct: "0.35" }, RULES)).toBe(118.46)
  })
  it("100 / 0.55 * 0.995 = 180.91", () => {
    expect(salePrice({ code: "X1", price_purchase: "100", coefficient: "0.995", margin_pct: "0.45" }, RULES)).toBe(180.91)
  })
  it("null purchase -> null", () => {
    expect(salePrice({ code: "X1", price_purchase: null, coefficient: "1", margin_pct: null }, RULES)).toBeNull()
  })
  it("empty coefficient/purchase -> null (not a fake 0)", () => {
    expect(salePrice({ code: "X1", price_purchase: "100", coefficient: "", margin_pct: "0.35" }, RULES)).toBeNull()
    expect(salePrice({ code: "X1", price_purchase: "", coefficient: "1", margin_pct: null }, RULES)).toBeNull()
  })
  it("empty margin string is treated as no override", () => {
    expect(resolveMargin({ code: "ESPA1", margin_pct: "" }, RULES)).toEqual({ margin: 0.35, source: "default" })
  })
  it("longest prefix wins, order-independent", () => {
    const r = { default: 0.35, AK: 0.34, AKX: 0.3 }
    expect(resolveMargin({ code: "AKX1", margin_pct: null }, r)).toEqual({ margin: 0.3, source: "prefix", prefix: "AKX" })
  })
})
