import { useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

export type TreeNode = { id: number; parent_id: number | null; name: string }

export function TreeView({
  nodes,
  selectedId,
  onSelect,
}: {
  nodes: TreeNode[]
  selectedId: number | null
  onSelect: (id: number) => void
}) {
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set())
  const byParent = new Map<number | null, TreeNode[]>()
  nodes.forEach((n) => {
    const list = byParent.get(n.parent_id) ?? []
    list.push(n)
    byParent.set(n.parent_id, list)
  })

  const toggle = (id: number) =>
    setCollapsed((s) => {
      const next = new Set(s)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const render = (parentId: number | null, depth: number, seen: Set<number>): React.ReactNode =>
    (byParent.get(parentId) ?? [])
      .filter((n) => !seen.has(n.id)) // defensive: bad data with a cycle won't recurse forever
      .map((n) => {
      const children = byParent.get(n.id) ?? []
      const isCollapsed = collapsed.has(n.id)
      return (
        <div key={n.id}>
          <div
            className={cn(
              "flex cursor-pointer items-center gap-1 rounded-md px-2 py-1 text-sm hover:bg-accent/50",
              selectedId === n.id && "bg-accent text-accent-foreground",
            )}
            style={{ paddingLeft: depth * 16 + 8 }}
            onClick={() => onSelect(n.id)}
          >
            {children.length > 0 ? (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  toggle(n.id)
                }}
              >
                {isCollapsed ? <ChevronRight className="size-3.5" /> : <ChevronDown className="size-3.5" />}
              </button>
            ) : (
              <span className="w-3.5" />
            )}
            {n.name}
          </div>
          {!isCollapsed && render(n.id, depth + 1, new Set(seen).add(n.id))}
        </div>
      )
    })

  return <div>{render(null, 0, new Set())}</div>
}
