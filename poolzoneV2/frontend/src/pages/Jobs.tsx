import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { Badge, Button, Card } from "@/components/ui"

const statusTone: Record<string, string> = {
  success: "green",
  failed: "red",
  running: "amber",
  skipped: "slate",
}

export default function Jobs() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ["jobs"], queryFn: api.listJobs })

  const sync = useMutation({
    mutationFn: () => api.triggerSync("pooltechnika"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })
  const exp = useMutation({
    mutationFn: () => api.triggerExport(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["jobs"] }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-900">Jobs</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => sync.mutate()} disabled={sync.isPending}>
            {sync.isPending ? "Syncing…" : "Sync pooltechnika"}
          </Button>
          <Button onClick={() => exp.mutate()} disabled={exp.isPending}>
            {exp.isPending ? "Exporting…" : "Export XML"}
          </Button>
        </div>
      </div>
      <Card>
        <table className="w-full text-sm">
          <thead className="border-b border-slate-200 text-left text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">#</th>
              <th className="px-4 py-2 font-medium">Kind</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Stats</th>
            </tr>
          </thead>
          <tbody>
            {data?.map((j) => (
              <tr key={j.id} className="border-b border-slate-100">
                <td className="px-4 py-2 text-slate-400">{j.id}</td>
                <td className="px-4 py-2">{j.kind}</td>
                <td className="px-4 py-2">
                  <Badge tone={statusTone[j.status] ?? "slate"}>{j.status}</Badge>
                </td>
                <td className="px-4 py-2 font-mono text-xs text-slate-500">
                  {JSON.stringify(j.stats)}
                </td>
              </tr>
            ))}
            {data?.length === 0 && (
              <tr>
                <td className="px-4 py-6 text-slate-400" colSpan={4}>
                  No runs yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
