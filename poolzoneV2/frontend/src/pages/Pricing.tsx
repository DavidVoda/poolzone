import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { api, type MarginRule } from "@/lib/api"
import { Button, Card, Input } from "@/components/ui"

export default function Pricing() {
  const { data } = useQuery({ queryKey: ["rules"], queryFn: api.listRules })
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">Pricing rules</h1>
      <p className="text-sm text-slate-500">
        Default margins by scope. A product’s own margin, when set, overrides these.
      </p>
      <Card className="max-w-xl divide-y divide-slate-100">
        {data?.map((r) => <RuleRow key={r.id} rule={r} />)}
        {data?.length === 0 && <p className="p-4 text-slate-400">No rules seeded.</p>}
      </Card>
    </div>
  )
}

function RuleRow({ rule }: { rule: MarginRule }) {
  const qc = useQueryClient()
  const [margin, setMargin] = useState(rule.margin_pct)
  const save = useMutation({
    mutationFn: () => api.updateRule(rule.id, margin),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  })
  return (
    <div className="flex items-center gap-4 p-4">
      <div className="flex-1">
        <div className="text-sm font-medium text-slate-800">
          {rule.scope}
          {rule.match_value ? ` · ${rule.match_value}` : ""}
        </div>
        <div className="text-xs text-slate-400">margin fraction (0.35 = 35%)</div>
      </div>
      <Input value={margin} onChange={(e) => setMargin(e.target.value)} className="w-28" />
      <Button variant="outline" onClick={() => save.mutate()} disabled={save.isPending}>
        Save
      </Button>
    </div>
  )
}
