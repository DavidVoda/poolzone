import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Play } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { PageHeader } from "@/components/app/PageHeader"
import { StatusBadge } from "@/components/app/StatusBadge"
import { client, unwrap, type JobRun } from "@/lib/api"
import { formatDateTime } from "@/lib/format"

const KIND_LABELS: Record<string, string> = { sync: "Sync", export: "Export" }

function duration(run: JobRun) {
  if (!run.started_at || !run.finished_at) return "—"
  const s = (new Date(run.finished_at).getTime() - new Date(run.started_at).getTime()) / 1000
  return s < 60 ? `${Math.round(s)} s` : `${Math.round(s / 60)} min`
}

export default function Jobs() {
  const queryClient = useQueryClient()
  const [detail, setDetail] = useState<JobRun | null>(null)

  const { data: runs } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => unwrap(client.GET("/api/jobs", { params: { query: { limit: 50 } } })),
    refetchInterval: (q) => (q.state.data?.some((j) => j.status === "running") ? 5_000 : 60_000),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["jobs"] })
    queryClient.invalidateQueries({ queryKey: ["jobs", "latest"] })
    queryClient.invalidateQueries({ queryKey: ["products"] })
  }

  const sync = useMutation({
    mutationFn: () =>
      unwrap(client.POST("/api/jobs/sync/{supplier_code}", { params: { path: { supplier_code: "pooltechnika" } } })),
    onSuccess: () => {
      toast.success("Sync dokončen")
      invalidate()
    },
    onError: (e: Error) => {
      toast.error(e.message)
      invalidate()
    },
  })

  const exportJob = useMutation({
    mutationFn: () => unwrap(client.POST("/api/jobs/export")),
    onSuccess: () => {
      toast.success("Export dokončen")
      invalidate()
    },
    onError: (e: Error) => {
      toast.error(e.message)
      invalidate()
    },
  })

  return (
    <>
      <PageHeader
        title="Úlohy"
        actions={
          <>
            <Button size="sm" onClick={() => sync.mutate()} disabled={sync.isPending}>
              <Play className="size-4" /> {sync.isPending ? "Sync běží…" : "Sync teď"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => exportJob.mutate()} disabled={exportJob.isPending}>
              <Play className="size-4" /> {exportJob.isPending ? "Export běží…" : "Export teď"}
            </Button>
          </>
        }
      />
      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-sky-50/60 hover:bg-sky-50/60">
              <TableHead className="text-sky-800">Úloha</TableHead>
              <TableHead className="text-sky-800">Stav</TableHead>
              <TableHead className="text-sky-800">Spuštěno</TableHead>
              <TableHead className="text-sky-800">Trvání</TableHead>
              <TableHead className="text-sky-800">Statistiky</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs?.map((run) => (
              <TableRow key={run.id} className="cursor-pointer" onClick={() => setDetail(run)}>
                <TableCell>{KIND_LABELS[run.kind] ?? run.kind}</TableCell>
                <TableCell>
                  <StatusBadge status={run.status} />
                </TableCell>
                <TableCell>{formatDateTime(run.started_at)}</TableCell>
                <TableCell>{duration(run)}</TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {Object.entries(run.stats)
                    .filter(([k, v]) => k !== "errors" && (typeof v === "number" || typeof v === "string"))
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(" · ") || "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Sheet open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <SheetContent className="w-[480px] overflow-y-auto sm:max-w-[480px]">
          {detail && (
            <>
              <SheetHeader>
                <SheetTitle>
                  {KIND_LABELS[detail.kind] ?? detail.kind} #{detail.id} <StatusBadge status={detail.status} />
                </SheetTitle>
              </SheetHeader>
              <div className="space-y-4 px-4 pb-6">
                {detail.error && (
                  <pre className="whitespace-pre-wrap rounded-md bg-red-50 p-3 text-xs text-red-700">{detail.error}</pre>
                )}
                {Array.isArray(detail.stats.errors) && detail.stats.errors.length > 0 && (
                  <div>
                    <h4 className="mb-1 text-sm font-medium">Chyby po produktech</h4>
                    <ul className="space-y-1 text-xs text-red-700">
                      {(detail.stats.errors as unknown[]).map((e, i) => (
                        <li key={i} className="rounded bg-red-50 p-1.5">
                          {typeof e === "string" ? e : JSON.stringify(e)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  <h4 className="mb-1 text-sm font-medium">Statistiky</h4>
                  <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs">
                    {JSON.stringify(detail.stats, null, 2)}
                  </pre>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </>
  )
}
