"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCan } from "@/hooks/use-can";
import {
  createSupplier,
  deleteSupplier,
  listSuppliers,
  updateSupplier,
  type SupplierResponse,
} from "@/lib/api/suppliers-api";
import { errorMessage } from "@/lib/format";

type FormState = {
  name: string;
  trade_name: string;
  document: string;
  state_registration: string;
  email: string;
  phone: string;
  is_active: boolean;
};

const emptyForm: FormState = {
  name: "",
  trade_name: "",
  document: "",
  state_registration: "",
  email: "",
  phone: "",
  is_active: true,
};

export default function SuppliersPage() {
  const canWrite = useCan("suppliers", "write");
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<SupplierResponse | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const trimmedSearch = search.trim();
  const searchDigits = trimmedSearch.replace(/\D/g, "");
  const searchableCharacters = trimmedSearch.replace(/\s/g, "").length;
  const searchByDocument =
    searchDigits.length > 0 && searchDigits.length >= searchableCharacters / 2;

  const list = useQuery({
    queryKey: ["suppliers", search],
    queryFn: () =>
      listSuppliers({
        name: trimmedSearch && !searchByDocument ? trimmedSearch : undefined,
        document: trimmedSearch && searchByDocument ? searchDigits : undefined,
      }),
  });

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name.trim(),
        trade_name: form.trade_name.trim() || null,
        document: form.document.replace(/\D/g, ""),
        state_registration: form.state_registration.trim() || null,
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        is_active: form.is_active,
      };
      if (editing) return updateSupplier(editing.id, payload);
      return createSupplier(payload);
    },
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteSupplier(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  return (
    <RequirePermission module="suppliers">
      <PageHeader
        title="Fornecedores"
        description="Cadastro de fornecedores para compras."
        actionLabel={canWrite ? "Novo fornecedor" : undefined}
        onAction={
          canWrite
            ? () => {
                setEditing(null);
                setForm(emptyForm);
                setError(null);
                setOpen(true);
              }
            : undefined
        }
      />

      <div className="mb-4">
        <Input
          placeholder="Buscar por nome ou CNPJ…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </div>

      <ErrorAlert message={error || (list.error ? errorMessage(list.error) : null)} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhum fornecedor encontrado." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>CNPJ</TableHead>
                <TableHead>IE</TableHead>
                <TableHead>Contato</TableHead>
                <TableHead>Status</TableHead>
                {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((item) => (
                <TableRow key={item.id}>
                  <TableCell>
                    <div className="font-medium">{item.name}</div>
                    {item.trade_name ? (
                      <div className="text-xs text-muted-foreground">
                        {item.trade_name}
                      </div>
                    ) : null}
                  </TableCell>
                  <TableCell className="font-mono text-xs">{item.document}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {item.state_registration || "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {item.email || item.phone || "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={item.is_active ? "default" : "secondary"}>
                      {item.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  {canWrite ? (
                    <TableCell className="space-x-2 text-right">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditing(item);
                          setForm({
                            name: item.name,
                            trade_name: item.trade_name ?? "",
                            document: item.document,
                            state_registration: item.state_registration ?? "",
                            email: item.email ?? "",
                            phone: item.phone ?? "",
                            is_active: item.is_active,
                          });
                          setError(null);
                          setOpen(true);
                        }}
                      >
                        Editar
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Excluir fornecedor "${item.name}"?`)) {
                            remove.mutate(item.id);
                          }
                        }}
                      >
                        Excluir
                      </Button>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Editar fornecedor" : "Novo fornecedor"}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Razão social</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Nome fantasia</Label>
              <Input
                value={form.trade_name}
                onChange={(e) =>
                  setForm((p) => ({ ...p, trade_name: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>CNPJ</Label>
              <Input
                value={form.document}
                onChange={(e) =>
                  setForm((p) => ({ ...p, document: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Inscrição estadual</Label>
              <Input
                value={form.state_registration}
                onChange={(e) =>
                  setForm((p) => ({ ...p, state_registration: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>E-mail</Label>
              <Input
                value={form.email}
                onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Telefone</Label>
              <Input
                value={form.phone}
                onChange={(e) => setForm((p) => ({ ...p, phone: e.target.value }))}
              />
            </div>
            <label className="flex items-center gap-2 self-end text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) =>
                  setForm((p) => ({ ...p, is_active: e.target.checked }))
                }
              />
              Ativo
            </label>
          </div>
          <ErrorAlert message={error} />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={
                !form.name.trim() ||
                !form.document.replace(/\D/g, "") ||
                save.isPending
              }
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </RequirePermission>
  );
}
