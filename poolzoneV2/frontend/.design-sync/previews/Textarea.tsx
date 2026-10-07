import { Textarea } from "frontend"

export const Default = () => (
  <Textarea placeholder="Popis produktu…" rows={4} className="w-80" />
)
export const WithValue = () => (
  <Textarea
    className="w-80"
    rows={4}
    defaultValue={"Kvalitní bazénové těsnění.\nVhodné pro filtraci ESPA."}
  />
)
