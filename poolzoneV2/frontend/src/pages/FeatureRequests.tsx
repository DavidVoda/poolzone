import { useMemo, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { PageHeader } from "@/components/app/PageHeader"
import { StatusBadge } from "@/components/app/StatusBadge"
import { Field } from "@/components/form/Field"
import { client, unwrap, type FeatureRequest } from "@/lib/api"
import { formatDateTime } from "@/lib/format"

const PRIORITY_LABELS: Record<string, string> = { low: "nízká", normal: "normální", high: "vysoká" }
// Statuses where the agent may be working / about to pick up — poll these.
const ACTIVE = new Set(["ready_for_plan", "planning", "ready_for_impl", "implementing"])
type Sort = "updated" | "created" | "priority"
const PRIORITY_RANK: Record<string, number> = { high: 0, normal: 1, low: 2 }

export default function FeatureRequests() {
  const queryClient = useQueryClient()
  const [detailId, setDetailId] = useState<number | null>(null)
  const [status, setStatus] = useState("all")
  const [priority, setPriority] = useState("all")
  const [tag, setTag] = useState("all")
  const [sort, setSort] = useState<Sort>("updated")

  const { data: requests } = useQuery({
    queryKey: ["feature-requests"],
    queryFn: () => unwrap(client.GET("/api/feature-requests")),
    refetchInterval: (q) => (q.state.data?.some((r) => ACTIVE.has(r.status)) ? 4_000 : false),
  })

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["feature-requests"] })
  const tags = useMemo(
    () => [...new Set((requests ?? []).map((r) => r.tag).filter((t): t is string => !!t))],
    [requests],
  )

  const shown = useMemo(() => {
    let list = (requests ?? []).filter(
      (r) =>
        (status === "all" || r.status === status) &&
        (priority === "all" || r.priority === priority) &&
        (tag === "all" || r.tag === tag),
    )
    list = [...list].sort((a, b) => {
      if (sort === "priority") return PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]
      return b[sort === "created" ? "created_at" : "updated_at"].localeCompare(
        a[sort === "created" ? "created_at" : "updated_at"],
      )
    })
    return list
  }, [requests, status, priority, tag, sort])

  const detail = requests?.find((r) => r.id === detailId) ?? null

  return (
    <>
      <PageHeader title="Požadavky" actions={<NewRequestDialog onCreated={invalidate} />} />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <FilterSelect value={status} onChange={setStatus} placeholder="Stav" options={STATUS_OPTS} />
        <FilterSelect
          value={priority}
          onChange={setPriority}
          placeholder="Priorita"
          options={Object.entries(PRIORITY_LABELS).map(([v, l]) => [v, l])}
        />
        <FilterSelect
          value={tag}
          onChange={setTag}
          placeholder="Oblast"
          options={tags.map((t) => [t, t])}
        />
        <Select value={sort} onValueChange={(v) => setSort(v as Sort)}>
          <SelectTrigger className="ml-auto w-44" size="sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="updated">Naposledy upraveno</SelectItem>
            <SelectItem value="created">Nejnovější</SelectItem>
            <SelectItem value="priority">Priorita</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((r) => (
          <button
            key={r.id}
            onClick={() => setDetailId(r.id)}
            className="flex flex-col gap-2 rounded-lg border bg-card p-4 text-left shadow-sm hover:border-primary/40"
          >
            <div className="flex items-center gap-2">
              <StatusBadge status={r.status} />
              <span className="ml-auto text-xs text-muted-foreground">{formatDateTime(r.updated_at)}</span>
            </div>
            <h3 className="font-medium leading-snug">{r.title}</h3>
            <p className="line-clamp-2 text-sm text-muted-foreground">{r.description}</p>
            <div className="mt-auto flex flex-wrap gap-1 pt-1 text-[11px]">
              <span className="rounded-full bg-muted px-2 py-0.5">{PRIORITY_LABELS[r.priority] ?? r.priority}</span>
              {r.tag && <span className="rounded-full bg-muted px-2 py-0.5">{r.tag}</span>}
            </div>
          </button>
        ))}
        {shown.length === 0 && <p className="text-muted-foreground">Žádné požadavky.</p>}
      </div>

      <Sheet open={!!detail} onOpenChange={(o) => !o && setDetailId(null)}>
        <SheetContent className="w-[560px] overflow-y-auto sm:max-w-[560px]">
          {detail && <Detail req={detail} onChanged={invalidate} />}
        </SheetContent>
      </Sheet>
    </>
  )
}

const STATUS_OPTS: [string, string][] = [
  ["draft", "koncept"],
  ["ready_for_plan", "k plánu"],
  ["planning", "plánuji"],
  ["planned", "naplánováno"],
  ["ready_for_impl", "k realizaci"],
  ["implementing", "realizuji"],
  ["implemented", "realizováno"],
]

function FilterSelect({
  value,
  onChange,
  placeholder,
  options,
}: {
  value: string
  onChange: (v: string) => void
  placeholder: string
  options: [string, string][]
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="w-40" size="sm">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">{placeholder}: vše</SelectItem>
        {options.map(([v, l]) => (
          <SelectItem key={v} value={v}>
            {l}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

function NewRequestDialog({ onCreated }: { onCreated: () => void }) {
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [priority, setPriority] = useState("normal")
  const [tag, setTag] = useState("")

  const create = useMutation({
    mutationFn: () =>
      unwrap(
        client.POST("/api/feature-requests", {
          body: { title, description, priority, tag: tag || null },
        }),
      ),
    onSuccess: () => {
      toast.success("Požadavek vytvořen")
      setOpen(false)
      setTitle("")
      setDescription("")
      setPriority("normal")
      setTag("")
      onCreated()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" /> Nový požadavek
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Nový požadavek</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Field label="Název">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Krátký titulek" />
          </Field>
          <Field label="Popis (user story)">
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={6}
              placeholder="Jako operátor chci…"
            />
          </Field>
          <div className="flex gap-3">
            <Field label="Priorita">
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(PRIORITY_LABELS).map(([v, l]) => (
                    <SelectItem key={v} value={v}>
                      {l}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Oblast (tag)">
              <Input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="ceny, produkty…" />
            </Field>
          </div>
        </div>
        <DialogFooter>
          <Button onClick={() => create.mutate()} disabled={!title || !description || create.isPending}>
            Vytvořit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Detail({ req, onChanged }: { req: FeatureRequest; onChanged: () => void }) {
  const [plan, setPlan] = useState(req.plan ?? "")
  const [note, setNote] = useState("")

  const move = useMutation({
    mutationFn: (body: { to: string; review_note?: string }) =>
      unwrap(
        client.POST("/api/feature-requests/{req_id}/transition", {
          params: { path: { req_id: req.id } },
          body,
        }),
      ),
    onSuccess: () => onChanged(),
    onError: (e: Error) => toast.error(e.message),
  })

  const savePlan = useMutation({
    mutationFn: () =>
      unwrap(
        client.PATCH("/api/feature-requests/{req_id}", {
          params: { path: { req_id: req.id } },
          body: { plan },
        }),
      ),
    onSuccess: () => {
      toast.success("Plán uložen")
      onChanged()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <>
      <SheetHeader>
        <SheetTitle className="flex items-center gap-2">
          #{req.id} {req.title} <StatusBadge status={req.status} />
        </SheetTitle>
      </SheetHeader>
      <div className="space-y-4 px-4 pb-8">
        <section>
          <h4 className="mb-1 text-sm font-medium">Popis</h4>
          <p className="whitespace-pre-wrap text-sm text-muted-foreground">{req.description}</p>
        </section>

        {req.error && (
          <pre className="whitespace-pre-wrap rounded-md bg-red-50 p-3 text-xs text-red-700">{req.error}</pre>
        )}

        {req.status === "planned" ? (
          <section>
            <h4 className="mb-1 text-sm font-medium">Plán (upravitelný)</h4>
            <Textarea value={plan} onChange={(e) => setPlan(e.target.value)} rows={14} className="font-mono text-xs" />
            <div className="mt-2 flex flex-wrap gap-2">
              <Button size="sm" variant="outline" onClick={() => savePlan.mutate()} disabled={savePlan.isPending}>
                Uložit plán
              </Button>
              <Button size="sm" onClick={() => move.mutate({ to: "ready_for_impl" })} disabled={move.isPending}>
                Připravit k realizaci
              </Button>
            </div>
            <div className="mt-3 space-y-1">
              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={2}
                placeholder="Poznámka pro přeplánování (agent ji uvidí)"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => move.mutate({ to: "draft", review_note: note || undefined })}
                disabled={move.isPending}
              >
                Zpět na koncept
              </Button>
            </div>
          </section>
        ) : req.plan ? (
          <section>
            <h4 className="mb-1 text-sm font-medium">Plán</h4>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-xs">{req.plan}</pre>
          </section>
        ) : null}

        {/* Operator-driven gates (agent picks up the ready_* states out of band) */}
        {req.status === "draft" && (
          <Button size="sm" onClick={() => move.mutate({ to: "ready_for_plan" })} disabled={move.isPending}>
            Připravit k plánu
          </Button>
        )}
        {req.status === "ready_for_plan" && (
          <p className="text-sm text-muted-foreground">Čeká na agenta (plán). Spusť „feature-runner“.</p>
        )}
        {req.status === "planning" && <p className="text-sm text-muted-foreground">Agent plánuje…</p>}
        {req.status === "ready_for_impl" && (
          <p className="text-sm text-muted-foreground">Čeká na agenta (realizace). Spusť „feature-runner“.</p>
        )}
        {req.status === "implementing" && <p className="text-sm text-muted-foreground">Agent realizuje…</p>}
        {req.status === "implemented" && (
          <div className="space-y-2">
            <p className="rounded-md bg-amber-50 p-2 text-sm text-amber-800">
              Změny jsou v pracovním stromu (bez commitu) — zkontroluj a commitni ručně.
            </p>
            <Button size="sm" variant="outline" onClick={() => move.mutate({ to: "draft" })} disabled={move.isPending}>
              Znovu od začátku
            </Button>
          </div>
        )}

        {req.execution_log && (
          <section>
            <h4 className="mb-1 text-sm font-medium">Průběh realizace</h4>
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md bg-muted p-3 text-xs">
              {req.execution_log}
            </pre>
          </section>
        )}
      </div>
    </>
  )
}
