import { Badge } from "frontend"

export const Variants = () => (
  <div className="flex flex-wrap items-center gap-2">
    <Badge>Aktivní</Badge>
    <Badge variant="secondary">Koncept</Badge>
    <Badge variant="destructive">Chyba</Badge>
    <Badge variant="outline">Archiv</Badge>
  </div>
)
