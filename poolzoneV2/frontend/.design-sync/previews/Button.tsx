import { Button } from "frontend"

export const Variants = () => (
  <div className="flex flex-wrap items-center gap-2">
    <Button>Uložit</Button>
    <Button variant="secondary">Zrušit</Button>
    <Button variant="outline">Filtr</Button>
    <Button variant="ghost">Detail</Button>
    <Button variant="destructive">Smazat</Button>
    <Button variant="link">Více</Button>
  </div>
)

export const Sizes = () => (
  <div className="flex items-center gap-2">
    <Button size="sm">Malé</Button>
    <Button>Výchozí</Button>
    <Button size="lg">Velké</Button>
  </div>
)

export const Disabled = () => <Button disabled>Nedostupné</Button>
