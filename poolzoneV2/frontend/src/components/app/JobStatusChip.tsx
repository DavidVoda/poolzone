import { useQuery } from "@tanstack/react-query"
import { client, unwrap } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { StatusBadge } from "./StatusBadge"

export function useLatestJob() {
  return useQuery({
    queryKey: ["jobs", "latest"],
    queryFn: () => unwrap(client.GET("/api/jobs", { params: { query: { limit: 1 } } })),
    refetchInterval: (q) => (q.state.data?.[0]?.status === "running" ? 5_000 : 60_000),
  })
}

export function JobStatusChip() {
  const { data } = useLatestJob()
  const job = data?.[0]
  if (!job) return null
  return (
    <div className="flex items-center gap-2 border-t px-4 py-3 text-xs text-muted-foreground">
      <StatusBadge status={job.status} />
      <span>
        {job.kind} · {formatDateTime(job.started_at)}
      </span>
    </div>
  )
}
