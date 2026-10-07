import { Checkbox, Label } from "frontend"

export const Checked = () => (
  <div className="flex items-center gap-2">
    <Checkbox id="a" defaultChecked />
    <Label htmlFor="a">Aktivní produkt</Label>
  </div>
)
export const Unchecked = () => (
  <div className="flex items-center gap-2">
    <Checkbox id="b" />
    <Label htmlFor="b">Zobrazit v exportu</Label>
  </div>
)
