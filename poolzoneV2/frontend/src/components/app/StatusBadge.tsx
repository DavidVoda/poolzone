import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useT } from "@/lib/i18n"

const STYLES: Record<string, string> = {
  success: "bg-emerald-100 text-emerald-700",
  running: "bg-cyan-100 text-cyan-700",
  failed: "bg-red-100 text-red-700",
  skipped: "bg-slate-100 text-slate-600",
  active: "bg-emerald-100 text-emerald-700",
  inactive: "bg-slate-100 text-slate-500",
  draft: "bg-slate-100 text-slate-600",
  ready_for_plan: "bg-amber-100 text-amber-700",
  planning: "bg-cyan-100 text-cyan-700",
  planned: "bg-indigo-100 text-indigo-700",
  ready_for_impl: "bg-amber-100 text-amber-700",
  implementing: "bg-cyan-100 text-cyan-700",
  implemented: "bg-emerald-100 text-emerald-700",
}

const LABELS: Record<string, string> = {
  success: "OK",
  running: "běží",
  failed: "chyba",
  skipped: "přeskočeno",
  active: "aktivní",
  inactive: "neaktivní",
  draft: "koncept",
  ready_for_plan: "k plánu",
  planning: "plánuji",
  planned: "naplánováno",
  ready_for_impl: "k realizaci",
  implementing: "realizuji",
  implemented: "realizováno",
}

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const { t } = useT()
  return (
    <Badge variant="secondary" className={cn(STYLES[status] ?? "bg-slate-100 text-slate-600", className)}>
      {t(LABELS[status] ?? status)}
    </Badge>
  )
}
