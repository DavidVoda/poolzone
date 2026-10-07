import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { KeyRound, Trash2, UserPlus } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Field } from "@/components/form/Field"
import { PageHeader } from "@/components/app/PageHeader"
import { client, unwrap, type User } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { useT } from "@/lib/i18n"

const initials = (name: string) =>
  name
    .split(/\s+/)
    .map((w) => w[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

function RoleBadge({ role }: { role: string }) {
  const { t } = useT()
  return (
    <Badge className={role === "admin" ? "bg-cyan-100 text-cyan-700" : "bg-slate-100 text-slate-600"}>
      {t(role === "admin" ? "Administrátor" : "Člen")}
    </Badge>
  )
}

export default function Users() {
  const { t } = useT()
  const qc = useQueryClient()
  const invalidate = () => qc.invalidateQueries({ queryKey: ["users"] })

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => unwrap(client.GET("/api/users")),
  })

  const patch = useMutation({
    mutationFn: (v: { id: number; body: { role?: string; active?: boolean; name?: string } }) =>
      unwrap(client.PATCH("/api/users/{user_id}", { params: { path: { user_id: v.id } }, body: v.body })),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  })

  const remove = useMutation({
    mutationFn: (id: number) =>
      unwrap(client.DELETE("/api/users/{user_id}", { params: { path: { user_id: id } } })),
    onSuccess: () => {
      toast.success(t("Uživatel smazán"))
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <>
      <PageHeader title={t("Uživatelé")} actions={<InviteDialog onDone={invalidate} />} />
      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{t("Uživatel")}</TableHead>
              <TableHead>{t("Role")}</TableHead>
              <TableHead>{t("Stav")}</TableHead>
              <TableHead>{t("Naposledy aktivní")}</TableHead>
              <TableHead className="w-0 text-right">{t("Akce")}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users?.map((u) => (
              <TableRow key={u.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <span className="flex size-8 items-center justify-center rounded-full bg-primary/10 font-mono text-xs font-semibold text-primary">
                      {initials(u.name)}
                    </span>
                    <div>
                      <div className="font-medium text-foreground">{u.name}</div>
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <Select value={u.role} onValueChange={(role) => patch.mutate({ id: u.id, body: { role } })}>
                    <SelectTrigger size="sm" className="w-36">
                      <SelectValue>
                        <RoleBadge role={u.role} />
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">{t("Administrátor")}</SelectItem>
                      <SelectItem value="member">{t("Člen")}</SelectItem>
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <button
                    className="cursor-pointer"
                    onClick={() => patch.mutate({ id: u.id, body: { active: !u.active } })}
                    title={t("Přepnout stav")}
                  >
                    <Badge className={u.active ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"}>
                      {t(u.active ? "Aktivní" : "Neaktivní")}
                    </Badge>
                  </button>
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {u.last_active_at ? formatDateTime(u.last_active_at) : "—"}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    <ResetPasswordDialog user={u} />
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      title={t("Smazat")}
                      onClick={() => {
                        if (window.confirm(t("Smazat uživatele {name}?").replace("{name}", u.name)))
                          remove.mutate(u.id)
                      }}
                    >
                      <Trash2 className="size-4 text-red-500" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </>
  )
}

function InviteDialog({ onDone }: { onDone: () => void }) {
  const { t } = useT()
  const [open, setOpen] = useState(false)
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState("member")

  const create = useMutation({
    mutationFn: () =>
      unwrap(client.POST("/api/users", { body: { email, name, password, role } })),
    onSuccess: () => {
      toast.success(t("Uživatel vytvořen"))
      onDone()
      setOpen(false)
      setEmail("")
      setName("")
      setPassword("")
      setRole("member")
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus className="size-4" /> {t("Přidat uživatele")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("Nový uživatel")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <Field label={t("E-mail")}>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label={t("Jméno")}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t("Heslo")}>
            <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <Field label={t("Role")}>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">{t("Administrátor")}</SelectItem>
                <SelectItem value="member">{t("Člen")}</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </div>
        <DialogFooter>
          <Button
            onClick={() => create.mutate()}
            disabled={create.isPending || !email || !name || !password}
          >
            {t("Vytvořit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function ResetPasswordDialog({ user }: { user: User }) {
  const { t } = useT()
  const [open, setOpen] = useState(false)
  const [password, setPassword] = useState("")

  const reset = useMutation({
    mutationFn: () =>
      unwrap(
        client.POST("/api/users/{user_id}/password", {
          params: { path: { user_id: user.id } },
          body: { password },
        }),
      ),
    onSuccess: () => {
      toast.success(t("Heslo změněno"))
      setOpen(false)
      setPassword("")
    },
    onError: (e: Error) => toast.error(e.message),
  })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon-sm" title={t("Změnit heslo")}>
          <KeyRound className="size-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {t("Změnit heslo")} · {user.email}
          </DialogTitle>
        </DialogHeader>
        <Field label={t("Nové heslo")}>
          <Input type="password" autoFocus value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <DialogFooter>
          <Button onClick={() => reset.mutate()} disabled={reset.isPending || !password}>
            {t("Uložit")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
