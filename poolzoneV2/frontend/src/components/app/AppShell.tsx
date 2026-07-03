import { NavLink, Outlet } from "react-router-dom"
import { BarChart3, Coins, FolderTree, Package, Play, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { GlobalSearch } from "./GlobalSearch"
import { JobStatusChip } from "./JobStatusChip"

const NAV = [
  { to: "/", label: "Produkty", icon: Package, end: true },
  { to: "/categories", label: "Kategorie", icon: FolderTree },
  { to: "/pricing", label: "Ceny", icon: Coins },
  { to: "/suggestions", label: "Návrhy", icon: Sparkles, disabled: true },
  { to: "/competitors", label: "Konkurence", icon: BarChart3, disabled: true },
  { to: "/jobs", label: "Úlohy", icon: Play },
]

export function AppShell() {
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col border-r bg-sidebar">
        <div className="px-4 py-4 text-lg font-semibold text-primary">◍ Poolzone</div>
        <nav className="flex-1 space-y-1 px-2">
          {NAV.map(({ to, label, icon: Icon, end, disabled }) =>
            disabled ? (
              <span
                key={to}
                className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground/50"
              >
                <Icon className="size-4" /> {label}
                <span className="ml-auto rounded-full bg-muted px-2 text-[10px]">brzy</span>
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium",
                    isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:bg-accent/50",
                  )
                }
              >
                <Icon className="size-4" /> {label}
              </NavLink>
            ),
          )}
        </nav>
        <JobStatusChip />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b px-6 py-2.5">
          <GlobalSearch />
        </header>
        <main className="min-w-0 flex-1 px-6 py-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
