import type { ReactNode } from "react"

export function FormSection({ title, children, actions }: { title: string; children: ReactNode; actions?: ReactNode }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-medium text-sky-800">{title}</h3>
        {actions}
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  )
}
