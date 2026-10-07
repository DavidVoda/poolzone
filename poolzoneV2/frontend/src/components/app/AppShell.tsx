import { NavLink, Outlet } from "react-router-dom"
import { BarChart3, Coins, DownloadCloud, FolderTree, Lightbulb, LogOut, Package, Play, Sparkles, Users, Workflow } from "lucide-react"
import { cn } from "@/lib/utils"
import { useT } from "@/lib/i18n"
import { useLogout, useMe } from "@/lib/auth"
import { GlobalSearch } from "./GlobalSearch"
import { JobStatusChip } from "./JobStatusChip"

const NAV = [
  { to: "/", label: "Produkty", icon: Package, end: true },
  { to: "/categories", label: "Kategorie", icon: FolderTree },
  { to: "/feed-mapping", label: "Transformace", icon: Workflow },
  { to: "/feeds", label: "Import dat", icon: DownloadCloud },
  { to: "/pricing", label: "Ceny", icon: Coins },
  { to: "/feature-requests", label: "Požadavky", icon: Lightbulb },
  { to: "/suggestions", label: "Návrhy", icon: Sparkles, disabled: true },
  { to: "/competitors", label: "Konkurence", icon: BarChart3, disabled: true },
  { to: "/jobs", label: "Úlohy", icon: Play },
  { to: "/users", label: "Uživatelé", icon: Users },
]

function UserFooter() {
  const { data: me } = useMe()
  const logout = useLogout()
  const user = me?.user
  if (!user) return null
  const initials = user.name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()
  return (
    <div className="flex items-center gap-2.5 border-t border-sidebar-border px-4 py-3">
      <div className="flex size-8 items-center justify-center rounded-full bg-[#0e7490] text-xs font-semibold text-[#e0f7fa]">
        {initials}
      </div>
      <div className="min-w-0 flex-1 leading-tight">
        <div className="truncate text-[12.5px] font-semibold text-white">{user.name}</div>
        <div className="truncate text-[11px] text-sidebar-muted">{user.email}</div>
      </div>
      <button
        onClick={() => logout().then(() => window.location.reload())}
        title="Odhlásit"
        className="text-sidebar-foreground/60 hover:text-white"
      >
        <LogOut className="size-4" />
      </button>
    </div>
  )
}

export function AppShell() {
  const { t, lang, setLang } = useT()
  return (
    <div className="flex min-h-screen">
      <aside className="flex w-56 shrink-0 flex-col bg-sidebar text-sidebar-foreground">
        <div className="flex items-center gap-2.5 border-b border-sidebar-border px-4 py-4">
          <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-[#22d3ee] to-[#0891b2] font-display text-[15px] font-bold text-sidebar-primary-foreground">
            ◍
          </div>
          <div className="leading-tight">
            <div className="font-display text-[15px] font-bold text-white">Poolzone</div>
            <div className="text-[10px] uppercase tracking-[0.08em] text-sidebar-muted">Middleware</div>
          </div>
        </div>
        <nav className="flex-1 space-y-0.5 px-2.5 py-3.5">
          {NAV.map(({ to, label, icon: Icon, end, disabled }) =>
            disabled ? (
              <span
                key={to}
                className="flex items-center gap-2 rounded-md px-2.5 py-2 text-[13px] text-sidebar-foreground/40"
              >
                <Icon className="size-4" /> {t(label)}
                <span className="ml-auto rounded-full bg-white/10 px-2 font-mono text-[10px]">{t("brzy")}</span>
              </span>
            ) : (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-2.5 py-2 text-[13px] transition-colors",
                    isActive
                      ? "border-l-2 border-sidebar-primary bg-sidebar-accent font-semibold text-sidebar-accent-foreground"
                      : "text-sidebar-foreground hover:bg-white/5",
                  )
                }
              >
                <Icon className="size-4" /> {t(label)}
              </NavLink>
            ),
          )}
        </nav>
        <JobStatusChip />
        <UserFooter />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-4 border-b bg-card px-6 py-2.5">
          <GlobalSearch />
          <div className="ml-auto flex items-center rounded-md border text-xs">
            {(["cs", "en"] as const).map((l) => (
              <button
                key={l}
                onClick={() => setLang(l)}
                className={cn(
                  "px-2 py-1 font-medium uppercase first:rounded-l-md last:rounded-r-md",
                  lang === l ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-accent",
                )}
              >
                {l}
              </button>
            ))}
          </div>
        </header>
        <main className="min-w-0 flex-1 px-6 py-5">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
