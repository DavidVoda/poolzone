import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Search } from "lucide-react"
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { client, unwrap } from "@/lib/api"

export function GlobalSearch() {
  const [open, setOpen] = useState(false)
  const [q, setQ] = useState("")
  const navigate = useNavigate()

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    window.addEventListener("keydown", down)
    return () => window.removeEventListener("keydown", down)
  }, [])

  const { data } = useQuery({
    queryKey: ["search", q],
    queryFn: () => unwrap(client.GET("/api/products", { params: { query: { q, limit: 10 } } })),
    enabled: open && q.length >= 2,
  })

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex w-72 items-center gap-2 rounded-md bg-muted px-3 py-1.5 text-sm text-muted-foreground hover:bg-accent"
      >
        <Search className="size-4" /> Hledat kód / název / EAN… <kbd className="ml-auto text-xs">⌘K</kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen}>
        <Command shouldFilter={false}>
          <CommandInput placeholder="Kód, název nebo EAN…" value={q} onValueChange={setQ} />
          <CommandList>
            <CommandEmpty>Nic nenalezeno.</CommandEmpty>
            {data?.items.map((p) => (
              <CommandItem
                key={p.id}
                value={String(p.id)}
                onSelect={() => {
                  setOpen(false)
                  navigate(`/products/${p.id}`)
                }}
              >
                <span className="font-mono text-xs text-muted-foreground">{p.code}</span> {p.title}
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </CommandDialog>
    </>
  )
}
