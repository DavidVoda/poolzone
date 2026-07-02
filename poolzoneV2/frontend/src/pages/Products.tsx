import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Badge, Card, Input } from "@/components/ui"

export default function Products() {
  const [q, setQ] = useState("")
  const { data, isLoading } = useQuery({
    queryKey: ["products", q],
    queryFn: () => api.listProducts({ q: q || undefined }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Products</h1>
        <Input
          placeholder="Search code or title…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="max-w-xs"
        />
      </div>
      <Card>
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Code</th>
              <th className="px-4 py-2 font-medium">Title</th>
              <th className="px-4 py-2 font-medium">Stock</th>
              <th className="px-4 py-2 font-medium">Purchase</th>
              <th className="px-4 py-2 font-medium">Sale</th>
              <th className="px-4 py-2 font-medium">Active</th>
            </tr>
          </thead>
          <tbody>
            {isLoading && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={6}>
                  Loading…
                </td>
              </tr>
            )}
            {data?.map((p) => (
              <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="px-4 py-2 font-mono text-xs">
                  <Link to={`/products/${p.id}`} className="text-blue-600 hover:underline">
                    {p.code}
                  </Link>
                </td>
                <td className="px-4 py-2">{p.title ?? "—"}</td>
                <td className="px-4 py-2">{p.stock ?? "—"}</td>
                <td className="px-4 py-2">{p.price_purchase ?? "—"}</td>
                <td className="px-4 py-2">{p.sale_price ?? "—"}</td>
                <td className="px-4 py-2">
                  <Badge tone={p.active ? "green" : "slate"}>{p.active ? "yes" : "no"}</Badge>
                </td>
              </tr>
            ))}
            {data?.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={6}>
                  No products.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
