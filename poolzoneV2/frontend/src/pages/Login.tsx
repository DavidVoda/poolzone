import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Field } from "@/components/form/Field"
import { client, unwrap } from "@/lib/api"
import { useT } from "@/lib/i18n"

export default function Login() {
  const { t } = useT()
  const qc = useQueryClient()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  const login = useMutation({
    mutationFn: () =>
      unwrap(client.POST("/api/auth/login", { body: { email, password } })),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["me"] }),
  })

  return (
    <div className="flex min-h-screen items-center justify-center bg-sidebar p-4">
      <form
        onSubmit={(e) => {
          e.preventDefault()
          login.mutate()
        }}
        className="w-full max-w-sm rounded-2xl bg-card p-8 shadow-2xl"
      >
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-gradient-to-br from-[#22d3ee] to-[#0891b2] font-display text-base font-bold text-[#04222f]">
            ◍
          </div>
          <div className="font-display text-lg font-bold text-foreground">Poolzone</div>
        </div>
        <h1 className="mb-1 font-display text-xl font-semibold text-foreground">{t("Přihlášení")}</h1>
        <p className="mb-5 text-sm text-muted-foreground">{t("Zadejte přihlašovací údaje.")}</p>

        <div className="space-y-3">
          <Field label={t("E-mail")}>
            <Input
              type="email"
              autoFocus
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field label={t("Heslo")}>
            <Input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
        </div>

        {login.isError && (
          <p className="mt-3 text-sm text-destructive">{t("Neplatný e-mail nebo heslo.")}</p>
        )}

        <Button type="submit" className="mt-5 w-full" disabled={login.isPending || !email || !password}>
          {login.isPending ? t("Přihlašuji…") : t("Přihlásit se")}
        </Button>
      </form>
    </div>
  )
}
