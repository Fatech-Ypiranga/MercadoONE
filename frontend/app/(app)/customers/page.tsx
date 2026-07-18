"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

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
import {
  AddressFields,
  AddressFormState,
  addressPayload,
  addressReady,
  emptyAddress,
} from "@/components/address-fields";
import { useCan } from "@/hooks/use-can";
import {
  createCustomer,
  createCustomerAddress,
  deleteCustomer,
  deleteCustomerAddress,
  getCustomer,
  listCustomers,
  updateCustomer,
  updateCustomerAddress,
  type CustomerAddressResponse,
  type CustomerResponse,
} from "@/lib/api/customers-api";
import { errorMessage } from "@/lib/format";

type FormState = {
  name: string;
  document: string;
  email: string;
  phone: string;
  customer_type: "F" | "J";
  ie_indicator: "1" | "2" | "9";
  is_active: boolean;
};

const emptyForm: FormState = {
  name: "",
  document: "",
  email: "",
  phone: "",
  customer_type: "F",
  ie_indicator: "9",
  is_active: true,
};

export default function CustomersPage() {
  const canWrite = useCan("customers", "write");
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CustomerResponse | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [createAddress, setCreateAddress] = useState<AddressFormState>(emptyAddress);
  const [includeAddress, setIncludeAddress] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const [addressesFor, setAddressesFor] = useState<CustomerResponse | null>(null);
  const [addressForm, setAddressForm] = useState<AddressFormState>(emptyAddress);
  const [editingAddress, setEditingAddress] =
    useState<CustomerAddressResponse | null>(null);
  const [addressError, setAddressError] = useState<string | null>(null);

  const list = useQuery({ queryKey: ["customers"], queryFn: listCustomers });

  const detail = useQuery({
    queryKey: ["customers", addressesFor?.id, "detail"],
    queryFn: () => getCustomer(addressesFor!.id),
    enabled: addressesFor != null,
  });

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return list.data ?? [];
    return (list.data ?? []).filter(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.document.includes(q) ||
        (c.email ?? "").toLowerCase().includes(q),
    );
  }, [list.data, search]);

  useEffect(() => {
    if (!editingAddress) {
      setAddressForm(emptyAddress);
      return;
    }
    setAddressForm({
      description: editingAddress.description,
      zip_code: editingAddress.zip_code,
      street: editingAddress.street,
      number: editingAddress.number,
      complement: editingAddress.complement ?? "",
      neighborhood: editingAddress.neighborhood,
      city: editingAddress.city,
      state: editingAddress.state,
      ibge_code: editingAddress.ibge_code ?? "",
    });
  }, [editingAddress]);

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name.trim(),
        document: form.document.replace(/\D/g, ""),
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        customer_type: form.customer_type,
        ie_indicator: form.ie_indicator,
        is_active: form.is_active,
        addresses:
          !editing && includeAddress && addressReady(createAddress)
            ? [addressPayload(createAddress)]
            : [],
      };
      if (editing) {
        return updateCustomer(editing.id, {
          name: payload.name,
          document: payload.document,
          email: payload.email,
          phone: payload.phone,
          customer_type: payload.customer_type,
          ie_indicator: payload.ie_indicator,
          is_active: payload.is_active,
        });
      }
      return createCustomer(payload);
    },
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
      setCreateAddress(emptyAddress);
      setIncludeAddress(false);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteCustomer(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const saveAddress = useMutation({
    mutationFn: async () => {
      if (!addressesFor) throw new Error("Cliente não selecionado");
      const body = addressPayload(addressForm);
      if (editingAddress) {
        return updateCustomerAddress(addressesFor.id, editingAddress.id, body);
      }
      return createCustomerAddress(addressesFor.id, body);
    },
    onSuccess: async () => {
      setAddressError(null);
      setEditingAddress(null);
      setAddressForm(emptyAddress);
      await qc.invalidateQueries({
        queryKey: ["customers", addressesFor?.id, "detail"],
      });
    },
    onError: (err) => setAddressError(errorMessage(err)),
  });

  const removeAddress = useMutation({
    mutationFn: (addressId: number) => {
      if (!addressesFor) throw new Error("Cliente não selecionado");
      return deleteCustomerAddress(addressesFor.id, addressId);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({
        queryKey: ["customers", addressesFor?.id, "detail"],
      });
    },
    onError: (err) => setAddressError(errorMessage(err)),
  });

  return (
    <RequirePermission module="customers">
      <PageHeader
        title="Clientes"
        description="Cadastro de clientes PF/PJ e endereços."
        actionLabel={canWrite ? "Novo cliente" : undefined}
        onAction={
          canWrite
            ? () => {
                setEditing(null);
                setForm(emptyForm);
                setCreateAddress(emptyAddress);
                setIncludeAddress(false);
                setError(null);
                setOpen(true);
              }
            : undefined
        }
      />

      <div className="mb-4">
        <Input
          placeholder="Buscar por nome, documento ou e-mail…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </div>

      <ErrorAlert message={error || (list.error ? errorMessage(list.error) : null)} />

      {list.isLoading ? (
        <LoadingState />
      ) : !filtered.length ? (
        <EmptyState message="Nenhum cliente encontrado." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Documento</TableHead>
                <TableHead>Tipo</TableHead>
                <TableHead>Contato</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Ações</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell className="font-mono text-xs">{item.document}</TableCell>
                  <TableCell>{item.customer_type === "J" ? "PJ" : "PF"}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {item.email || item.phone || "—"}
                  </TableCell>
                  <TableCell>
                    <Badge variant={item.is_active ? "default" : "secondary"}>
                      {item.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  <TableCell className="space-x-2 text-right">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setAddressesFor(item);
                        setEditingAddress(null);
                        setAddressForm(emptyAddress);
                        setAddressError(null);
                      }}
                    >
                      Endereços
                    </Button>
                    {canWrite ? (
                      <>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditing(item);
                            setForm({
                              name: item.name,
                              document: item.document,
                              email: item.email ?? "",
                              phone: item.phone ?? "",
                              customer_type: item.customer_type,
                              ie_indicator: item.ie_indicator,
                              is_active: item.is_active,
                            });
                            setIncludeAddress(false);
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
                            if (confirm(`Excluir cliente "${item.name}"?`)) {
                              remove.mutate(item.id);
                            }
                          }}
                        >
                          Excluir
                        </Button>
                      </>
                    ) : null}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Editar cliente" : "Novo cliente"}
            </DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Nome</Label>
              <Input
                value={form.name}
                onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>CPF/CNPJ</Label>
              <Input
                value={form.document}
                onChange={(e) =>
                  setForm((p) => ({ ...p, document: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Tipo</Label>
              <select
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                value={form.customer_type}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    customer_type: e.target.value as "F" | "J",
                  }))
                }
              >
                <option value="F">Pessoa física</option>
                <option value="J">Pessoa jurídica</option>
              </select>
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
            <label className="flex items-center gap-2 self-end text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) =>
                  setForm((p) => ({ ...p, is_active: e.target.checked }))
                }
              />
              Ativo
            </label>

            {!editing ? (
              <div className="space-y-3 border-t border-border pt-3 sm:col-span-2">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={includeAddress}
                    onChange={(e) => setIncludeAddress(e.target.checked)}
                  />
                  Incluir endereço agora
                </label>
                {includeAddress ? (
                  <AddressFields
                    form={createAddress}
                    onChange={setCreateAddress}
                  />
                ) : null}
              </div>
            ) : null}
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
                (includeAddress && !addressReady(createAddress)) ||
                save.isPending
              }
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={addressesFor != null}
        onOpenChange={(next) => {
          if (!next) {
            setAddressesFor(null);
            setEditingAddress(null);
            setAddressForm(emptyAddress);
            setAddressError(null);
          }
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Endereços — {addressesFor?.name ?? "Cliente"}
            </DialogTitle>
          </DialogHeader>

          {detail.isLoading ? (
            <LoadingState />
          ) : detail.error ? (
            <ErrorAlert message={errorMessage(detail.error)} />
          ) : (
            <div className="space-y-4">
              {!detail.data?.addresses?.length ? (
                <EmptyState message="Nenhum endereço cadastrado." />
              ) : (
                <div className="rounded-xl border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Descrição</TableHead>
                        <TableHead>Endereço</TableHead>
                        <TableHead>Cidade/UF</TableHead>
                        {canWrite ? (
                          <TableHead className="text-right">Ações</TableHead>
                        ) : null}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {detail.data.addresses.map((addr) => (
                        <TableRow key={addr.id}>
                          <TableCell>{addr.description}</TableCell>
                          <TableCell className="text-sm">
                            {addr.street}, {addr.number}
                            {addr.complement ? ` — ${addr.complement}` : ""}
                            <div className="text-xs text-muted-foreground">
                              CEP {addr.zip_code} · {addr.neighborhood}
                            </div>
                          </TableCell>
                          <TableCell>
                            {addr.city}/{addr.state}
                          </TableCell>
                          {canWrite ? (
                            <TableCell className="space-x-2 text-right">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setEditingAddress(addr);
                                  setAddressError(null);
                                }}
                              >
                                Editar
                              </Button>
                              <Button
                                type="button"
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                  if (
                                    confirm(
                                      `Excluir endereço "${addr.description}"?`,
                                    )
                                  ) {
                                    removeAddress.mutate(addr.id);
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

              {canWrite ? (
                <div className="grid gap-3 rounded-xl border border-border p-4">
                  <h3 className="text-sm font-semibold">
                    {editingAddress ? "Editar endereço" : "Novo endereço"}
                  </h3>
                  <AddressFields form={addressForm} onChange={setAddressForm} />
                  <ErrorAlert message={addressError} />
                  <div className="flex flex-wrap gap-2">
                    {editingAddress ? (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setEditingAddress(null);
                          setAddressForm(emptyAddress);
                          setAddressError(null);
                        }}
                      >
                        Cancelar edição
                      </Button>
                    ) : null}
                    <Button
                      type="button"
                      disabled={!addressReady(addressForm) || saveAddress.isPending}
                      onClick={() => saveAddress.mutate()}
                    >
                      {saveAddress.isPending
                        ? "Salvando…"
                        : editingAddress
                          ? "Atualizar endereço"
                          : "Adicionar endereço"}
                    </Button>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </RequirePermission>
  );
}
