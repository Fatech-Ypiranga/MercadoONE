"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { ErrorAlert, LoadingState } from "@/components/ui-states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useCan } from "@/hooks/use-can";
import { getMyCompany, updateMyCompany } from "@/lib/api/org-api";
import { errorMessage } from "@/lib/format";

type FormState = {
  legal_name: string;
  trade_name: string;
  document: string;
  state_registration: string;
  is_active: boolean;
  has_branches: boolean;
};

const emptyForm: FormState = {
  legal_name: "",
  trade_name: "",
  document: "",
  state_registration: "",
  is_active: true,
  has_branches: false,
};

export default function CompanyPage() {
  const canWrite = useCan("companies", "write");
  const { refreshUser } = useAuth();
  const qc = useQueryClient();
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const company = useQuery({
    queryKey: ["company", "me"],
    queryFn: getMyCompany,
  });

  useEffect(() => {
    if (!company.data) return;
    setForm({
      legal_name: company.data.legal_name,
      trade_name: company.data.trade_name ?? "",
      document: company.data.document,
      state_registration: company.data.state_registration ?? "",
      is_active: company.data.is_active,
      has_branches: company.data.has_branches,
    });
  }, [company.data]);

  const save = useMutation({
    mutationFn: () =>
      updateMyCompany({
        legal_name: form.legal_name.trim(),
        trade_name: form.trade_name.trim() || null,
        document: form.document.replace(/\D/g, ""),
        state_registration: form.state_registration.trim() || null,
        is_active: form.is_active,
        has_branches: form.has_branches,
      }),
    onSuccess: async () => {
      setError(null);
      setSaved(true);
      await qc.invalidateQueries({ queryKey: ["company", "me"] });
      await refreshUser();
    },
    onError: (err) => {
      setSaved(false);
      setError(errorMessage(err));
    },
  });

  return (
    <RequirePermission module="companies">
      <PageHeader
        title="Minha empresa"
        description="Dados cadastrais da empresa e opção de filiais."
      />

      <ErrorAlert message={error ?? (company.error ? errorMessage(company.error) : null)} />

      {company.isLoading ? (
        <LoadingState />
      ) : (
        <form
          className="max-w-xl space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            setSaved(false);
            save.mutate();
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="legal_name">Razão social</Label>
            <Input
              id="legal_name"
              value={form.legal_name}
              disabled={!canWrite}
              onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="trade_name">Nome fantasia</Label>
            <Input
              id="trade_name"
              value={form.trade_name}
              disabled={!canWrite}
              onChange={(e) => setForm({ ...form, trade_name: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="document">CNPJ</Label>
            <Input
              id="document"
              value={form.document}
              disabled={!canWrite}
              onChange={(e) => setForm({ ...form, document: e.target.value })}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="state_registration">Inscrição estadual</Label>
            <Input
              id="state_registration"
              value={form.state_registration}
              disabled={!canWrite}
              onChange={(e) =>
                setForm({ ...form, state_registration: e.target.value })
              }
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.has_branches}
              disabled={!canWrite}
              onChange={(e) =>
                setForm({ ...form, has_branches: e.target.checked })
              }
            />
            Empresa possui filiais (exibe o módulo Filiais)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              disabled={!canWrite}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Empresa ativa
          </label>

          {canWrite ? (
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Salvando…" : "Salvar"}
              </Button>
              {saved ? (
                <span className="text-sm text-muted-foreground">Salvo.</span>
              ) : null}
            </div>
          ) : null}
        </form>
      )}
    </RequirePermission>
  );
}
