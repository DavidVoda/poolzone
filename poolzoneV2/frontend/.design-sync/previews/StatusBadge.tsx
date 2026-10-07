import { StatusBadge } from "frontend"

export const JobStatuses = () => (
  <div className="flex flex-wrap items-center gap-2">
    <StatusBadge status="success" />
    <StatusBadge status="running" />
    <StatusBadge status="failed" />
    <StatusBadge status="skipped" />
  </div>
)

export const RequestStatuses = () => (
  <div className="flex flex-wrap items-center gap-2">
    <StatusBadge status="draft" />
    <StatusBadge status="planned" />
    <StatusBadge status="implementing" />
    <StatusBadge status="implemented" />
  </div>
)
