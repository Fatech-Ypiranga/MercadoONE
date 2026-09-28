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
import { createCompanyRegistration } from "@/lib/api/company-registrations-api";
import { ApiError } from "@/lib/api/client";

const SALES_CONTACT =
  process.env.NEXT_PUBLIC_SALES_CONTACT_URL || "mailto:vendas@pyerp.local";

type FormState = {
  legal_name: string;
  trade_name: string;
  document: string;
  state_registration: string;
  admin_name: string;
  admin_email: string;
  admin_cpf: string;
  admin_phone: string;
  declared_store_count: string;
};

const emptyForm: FormState = {
  legal_name: "",
  trade_name: "",
  document: "",
  state_registration: "",
  admin_name: "",
  admin_email: "",
  admin_cpf: "",
  admin_phone: "",
  declared_store_count: "1",
};

export default function CadastroPage() {
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const storeCount = Number(form.declared_store_count);
  const requiresSales = Number.isFinite(storeCount) && storeCount > 15;

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(false);

    if (requiresSales) {
      setError(
        "Empresas com mais de 15 lojas devem falar com o time de vendas.",
      );
      return;
    }

    setSubmitting(true);
    try {
      await createCompanyRegistration({
        legal_name: form.legal_name.trim(),
        trade_name: form.trade_name.trim() || null,
        document: form.document.replace(/\D/g, ""),
        state_registration: form.state_registration.trim() || null,
        admin_name: form.admin_name.trim(),
        admin_email: form.admin_email.trim(),
        admin_cpf: form.admin_cpf.replace(/\D/g, ""),
        admin_phone: form.admin_phone.trim() || null,
        declared_store_count: storeCount,
      });
      setSuccess(true);
      setForm(emptyForm);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Não foi possível enviar a solicitação. Tente novamente.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/40 px-4 py-10">
      <Card className="w-full max-w-lg border-border/80 shadow-sm">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-semibold tracking-tight">
            Cadastro de empresa
          </CardTitle>
          <CardDescription>
            Solicite acesso ao MercadoONE (até 15 lojas). Sua solicitação será
            avaliada pela equipe gestora.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {success ? (
            <div className="space-y-3 rounded-md bg-muted px-3 py-3 text-sm">
              <p>
                Solicitação enviada. Entraremos em contato após a avaliação.
              </p>
              <Link href="/login" className="text-sm font-medium underline">
                Voltar ao login
              </Link>
            </div>
          ) : (
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="legal_name">Razão social</Label>
                <Input
                  id="legal_name"
                  required
                  value={form.legal_name}
                  onChange={(e) =>
                    setForm({ ...form, legal_name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="trade_name">Nome fantasia</Label>
                <Input
                  id="trade_name"
                  value={form.trade_name}
                  onChange={(e) =>
                    setForm({ ...form, trade_name: e.target.value })
                  }
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="document">CNPJ</Label>
                  <Input
                    id="document"
                    required
                    value={form.document}
                    onChange={(e) =>
                      setForm({ ...form, document: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="declared_store_count">Qtd. de lojas</Label>
                  <Input
                    id="declared_store_count"
                    type="number"
                    min={1}
                    max={100}
                    required
                    value={form.declared_store_count}
                    onChange={(e) =>
                      setForm({ ...form, declared_store_count: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="state_registration">Inscrição estadual</Label>
                <Input
                  id="state_registration"
                  value={form.state_registration}
                  onChange={(e) =>
                    setForm({ ...form, state_registration: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin_name">Nome do administrador</Label>
                <Input
                  id="admin_name"
                  required
                  value={form.admin_name}
                  onChange={(e) =>
                    setForm({ ...form, admin_name: e.target.value })
                  }
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="admin_email">E-mail do admin</Label>
                  <Input
                    id="admin_email"
                    type="email"
                    required
                    value={form.admin_email}
                    onChange={(e) =>
                      setForm({ ...form, admin_email: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="admin_cpf">CPF do admin</Label>
                  <Input
                    id="admin_cpf"
                    required
                    value={form.admin_cpf}
                    onChange={(e) =>
                      setForm({ ...form, admin_cpf: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="admin_phone">Telefone</Label>
                <Input
                  id="admin_phone"
                  value={form.admin_phone}
                  onChange={(e) =>
                    setForm({ ...form, admin_phone: e.target.value })
                  }
                />
              </div>

              {requiresSales ? (
                <p className="rounded-md bg-muted px-3 py-2 text-sm">
                  Para 16+ lojas,{" "}
                  <a href={SALES_CONTACT} className="font-medium underline">
                    fale com o time de vendas
                  </a>
                  .
                </p>
              ) : null}

              {error ? (
                <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {error}
                </p>
              ) : null}

              <Button
                type="submit"
                className="w-full"
                disabled={submitting || requiresSales}
              >
                {submitting ? "Enviando…" : "Enviar solicitação"}
              </Button>

              <p className="text-center text-sm text-muted-foreground">
                Já tem conta?{" "}
                <Link href="/login" className="font-medium underline">
                  Entrar
                </Link>
              </p>
            </form>
          )}
        </CardContent>
      </Card>
    </main>
  );
}
