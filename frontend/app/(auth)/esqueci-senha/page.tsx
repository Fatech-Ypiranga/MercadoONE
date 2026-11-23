"use client";

import Link from "next/link";
import { useState } from "react";

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
import { requestPasswordReset } from "@/lib/api/auth-api";
import { ApiError } from "@/lib/api/client";

export default function ForgotPasswordPage() {
  const [companyDocument, setCompanyDocument] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!companyDocument.trim() || !email.trim()) {
      setError("Informe o CNPJ da empresa e o e-mail cadastrado.");
      return;
    }
    setSubmitting(true);
    try {
      await requestPasswordReset({
        company_document: companyDocument.replace(/\D/g, ""),
        email: email.trim(),
      });
      setSent(true);
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
    <main className="flex min-h-screen items-center justify-center bg-muted/40 px-4">
      <Card className="w-full max-w-md border-border/80 shadow-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-semibold tracking-tight">Esqueci minha senha</CardTitle>
          <CardDescription>
            Informe o CNPJ da empresa e o e-mail da sua conta para receber o link de redefinição.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <div className="space-y-4">
              <p role="status" className="rounded-md bg-muted px-3 py-2 text-sm">
                Se existir uma conta com esse e-mail, enviamos o link de redefinição. Confira também
                a caixa de spam.
              </p>
              <Link href="/login" className="text-sm font-medium underline">
                Voltar ao login
              </Link>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={onSubmit} noValidate>
              <div className="space-y-2">
                <Label htmlFor="company_document">CNPJ da empresa</Label>
                <Input
                  id="company_document"
                  autoComplete="organization"
                  placeholder="00.000.000/0001-91"
                  value={companyDocument}
                  onChange={(e) => setCompanyDocument(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
              {error ? (
                <p role="alert" className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              ) : null}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? "Enviando…" : "Enviar link"}
              </Button>
              <p className="text-center text-sm">
                <Link href="/login" className="font-medium underline">
                  Voltar ao login
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
