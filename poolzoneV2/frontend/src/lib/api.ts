import createClient from "openapi-fetch"
import type { paths } from "./api-types"

export const client = createClient<paths>({ baseUrl: "/" })

/** Unwrap an openapi-fetch result; throws Error with the FastAPI detail message. */
export async function unwrap<T>(p: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await p
  if (error !== undefined || data === undefined) {
    const detail = (error as { detail?: unknown })?.detail
    throw new Error(typeof detail === "string" ? detail : `${response.status} ${response.statusText}`)
  }
  return data
}

// Convenience row/entity aliases used across pages:
export type Product = paths["/api/products"]["get"]["responses"]["200"]["content"]["application/json"]["items"][number]
export type ProductDetail = paths["/api/products/{product_id}"]["get"]["responses"]["200"]["content"]["application/json"]
export type ProductUpdate = NonNullable<paths["/api/products/{product_id}"]["patch"]["requestBody"]>["content"]["application/json"]
export type Category = paths["/api/categories"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type CategoryMapping = paths["/api/categories/mappings"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type Supplier = paths["/api/suppliers"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type MarginRule = paths["/api/pricing/rules"]["get"]["responses"]["200"]["content"]["application/json"][number]
export type JobRun = paths["/api/jobs"]["get"]["responses"]["200"]["content"]["application/json"][number]
