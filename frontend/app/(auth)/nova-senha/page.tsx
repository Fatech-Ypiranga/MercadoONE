"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { checkPasswordResetToken, confirmPasswordReset } from "@/lib/api/auth-api";
import { ApiError } from "@/lib/api/client";

function NewPasswordForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<"checking" | "valid" | "invalid" | "done">("checking");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (token.length < 10) {
      setState("invalid");
      return;
    }
    checkPasswordResetToken(token)
      .then((r) => setState(r.valid ? "valid" : "invalid"))
      .catch(() => setState("invalid"));
  }, [token]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }
    if (password !== confirm) {
      setError("As senhas não conferem.");
      return;
    }
    setSubmitting(true);
    try {
      await confirmPasswordReset({ token, new_password: password });
      setState("done");
      setTimeout(() => router.replace("/login"), 2500);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível conectar à API. Tente novamente.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md border-border/80 shadow-sm">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-semibold tracking-tight">Nova senha</CardTitle>
        <CardDescription>Defina a nova senha da sua conta.</CardDescription>
      </CardHeader>
      <CardContent>
        {state === "checking" ? (
          <p role="status" className="text-sm text-muted-foreground">
            Verificando o link…
          </p>
        ) : null}

        {state === "invalid" ? (
          <div className="space-y-4">
            <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              Este link é inválido ou expirou.
            </p>
            <Link href="/esqueci-senha" className="text-sm font-medium underline">
              Pedir um novo link
            </Link>
          </div>
        ) : null}

        {state === "done" ? (
          <p role="status" className="rounded-md bg-muted px-3 py-2 text-sm">
            Senha alterada. Redirecionando para o login…
          </p>
        ) : null}

        {state === "valid" ? (
          <form className="space-y-4" onSubmit={onSubmit} noValidate>
            <div className="space-y-2">
              <Label htmlFor="new_password">Nova senha</Label>
              <Input
                id="new_password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password">Confirmar nova senha</Label>
              <Input
                id="confirm_password"
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
              />
            </div>
            {error ? (
              <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </p>
            ) : null}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Salvando…" : "Salvar nova senha"}
            </Button>
          </form>
        ) : null}
      </CardContent>
    </Card>
  );
}

export default function NewPasswordPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <Suspense fallback={null}>
        <NewPasswordForm />
      </Suspense>
    </main>
  );
}
