import { Label, Input } from "frontend"

export const WithInput = () => (
  <div className="grid w-72 gap-1.5">
    <Label htmlFor="code">Kód produktu</Label>
    <Input id="code" placeholder="ESPA1" />
  </div>
)
