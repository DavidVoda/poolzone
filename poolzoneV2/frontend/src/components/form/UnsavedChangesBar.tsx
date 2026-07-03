import { useEffect } from "react"
import { useBlocker } from "react-router-dom"
import { Button } from "@/components/ui/button"

type Props = { dirty: boolean; saving: boolean; onSave: () => void; onDiscard: () => void }

export function UnsavedChangesBar({ dirty, saving, onSave, onDiscard }: Props) {
  const blocker = useBlocker(dirty)

  useEffect(() => {
    if (blocker.state === "blocked") {
      if (window.confirm("Máte neuložené změny. Opustit stránku?")) blocker.proceed()
      else blocker.reset()
    }
  }, [blocker])

  useEffect(() => {
    if (!dirty) return
    const warn = (e: BeforeUnloadEvent) => e.preventDefault()
    window.addEventListener("beforeunload", warn)
    return () => window.removeEventListener("beforeunload", warn)
  }, [dirty])

  if (!dirty) return null
  return (
    <div className="fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-3 rounded-full border bg-background px-5 py-2.5 shadow-lg">
      <span className="text-sm">Neuložené změny</span>
      <Button size="sm" variant="ghost" onClick={onDiscard} disabled={saving}>
        Zahodit
      </Button>
      <Button size="sm" onClick={onSave} disabled={saving}>
        Uložit
      </Button>
    </div>
  )
}
