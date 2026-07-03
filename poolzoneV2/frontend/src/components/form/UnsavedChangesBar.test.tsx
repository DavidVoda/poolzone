import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { createMemoryRouter, RouterProvider } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"
import { UnsavedChangesBar } from "./UnsavedChangesBar"

const renderInRouter = (ui: React.ReactElement) =>
  render(<RouterProvider router={createMemoryRouter([{ path: "/", element: ui }])} />)

describe("UnsavedChangesBar", () => {
  it("hidden when clean", () => {
    renderInRouter(<UnsavedChangesBar dirty={false} saving={false} onSave={() => {}} onDiscard={() => {}} />)
    expect(screen.queryByText(/neuložené změny/i)).not.toBeInTheDocument()
  })

  it("shows and fires save/discard when dirty", async () => {
    const onSave = vi.fn()
    const onDiscard = vi.fn()
    renderInRouter(<UnsavedChangesBar dirty saving={false} onSave={onSave} onDiscard={onDiscard} />)
    expect(screen.getByText(/neuložené změny/i)).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "Uložit" }))
    expect(onSave).toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: "Zahodit" }))
    expect(onDiscard).toHaveBeenCalled()
  })
})
