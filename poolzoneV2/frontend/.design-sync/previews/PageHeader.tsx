import { PageHeader, Button } from "frontend"

export const WithActions = () => (
  <div className="w-[520px]">
    <PageHeader
      title="Produkty"
      actions={<><Button size="sm" variant="outline">Import</Button><Button size="sm">Nový</Button></>}
    />
  </div>
)

export const TitleOnly = () => (
  <div className="w-[520px]"><PageHeader title="Ceny" /></div>
)
