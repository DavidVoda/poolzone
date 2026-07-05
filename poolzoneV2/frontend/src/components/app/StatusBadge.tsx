import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

const STYLES: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  running: "bg-sky-100 text-sky-700",
  failed: "bg-red-100 text-red-700",
  skipped: "bg-slate-100 text-slate-600",
  active: "bg-green-100 text-green-700",
  inactive: "bg-slate-100 text-slate-500",
  draft: "bg-slate-100 text-slate-600",
  ready_for_plan: "bg-amber-100 text-amber-700",
  planning: "bg-sky-100 text-sky-700",
  planned: "bg-indigo-100 text-indigo-700",
  ready_for_impl: "bg-amber-100 text-amber-700",
  implementing: "bg-sky-100 text-sky-700",
  implemented: "bg-green-100 text-green-700",
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
  return (
    <Badge variant="secondary" className={cn(STYLES[status] ?? "bg-slate-100 text-slate-600", className)}>
      {LABELS[status] ?? status}
    </Badge>
  )
}
