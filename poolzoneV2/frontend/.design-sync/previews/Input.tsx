import { Input } from "frontend"

export const Default = () => <Input placeholder="Hledat produkt…" className="w-72" />
export const WithValue = () => <Input defaultValue="ESPA1 — Těsnění" className="w-72" />
export const Disabled = () => <Input placeholder="Nedostupné" disabled className="w-72" />
