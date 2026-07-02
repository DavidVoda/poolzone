import { NavLink, Route, Routes } from "react-router-dom"
import { cn } from "@/lib/utils"
import Products from "@/pages/Products"
import ProductDetail from "@/pages/ProductDetail"
import Pricing from "@/pages/Pricing"
import Jobs from "@/pages/Jobs"

const nav = [
  { to: "/", label: "Products", end: true },
  { to: "/pricing", label: "Pricing" },
  { to: "/jobs", label: "Jobs" },
]

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <span className="text-lg font-semibold text-slate-900">Poolzone</span>
          <nav className="flex gap-1">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm font-medium",
                    isActive ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100",
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Products />} />
          <Route path="/products/:id" element={<ProductDetail />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/jobs" element={<Jobs />} />
        </Routes>
      </main>
    </div>
  )
}
