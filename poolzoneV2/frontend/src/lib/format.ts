const czk = new Intl.NumberFormat("cs-CZ", { style: "currency", currency: "CZK", maximumFractionDigits: 2 })

export const formatKc = (v: string | number | null | undefined) => (v == null ? "—" : czk.format(Number(v)))

export const formatPct = (v: string | number | null | undefined) =>
  v == null ? "—" : `${(Number(v) * 100).toLocaleString("cs-CZ", { maximumFractionDigits: 1 })} %`

export const formatDateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("cs-CZ", { dateStyle: "short", timeStyle: "short" }) : "—"
