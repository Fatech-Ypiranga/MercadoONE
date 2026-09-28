"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
import { useEntityDialog } from "@/hooks/use-entity-dialog";
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

const customerSchema = z.object({
  name: z.string().trim().min(1, "Informe o nome"),
  document: z.string().refine((v) => v.replace(/\D/g, "").length > 0, "Informe o CPF/CNPJ"),
  email: z.string(),
  phone: z.string(),
  customer_type: z.enum(["F", "J"]),
  ie_indicator: z.enum(["1", "2", "9"]),
  is_active: z.boolean(),
});

type CustomerForm = z.infer<typeof customerSchema>;

const emptyForm: CustomerForm = {
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
  const dialog = useEntityDialog<CustomerResponse>();
  const [createAddress, setCreateAddress] = useState<AddressFormState>(emptyAddress);
  const [includeAddress, setIncludeAddress] = useState(false);
  const [search, setSearch] = useState("");

  const [addressesFor, setAddressesFor] = useState<CustomerResponse | null>(null);
  const [addressForm, setAddressForm] = useState<AddressFormState>(emptyAddress);
  const [editingAddress, setEditingAddress] =
    useState<CustomerAddressResponse | null>(null);
  const [addressError, setAddressError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CustomerForm>({
    resolver: zodResolver(customerSchema),
    defaultValues: emptyForm,
  });

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
    mutationFn: async (values: CustomerForm) => {
      const payload = {
        name: values.name,
        document: values.document.replace(/\D/g, ""),
        email: values.email.trim() || null,
        phone: values.phone.trim() || null,
        customer_type: values.customer_type,
        ie_indicator: values.ie_indicator,
        is_active: values.is_active,
        addresses:
          !dialog.editing && includeAddress && addressReady(createAddress)
            ? [addressPayload(createAddress)]
            : [],
      };
      if (dialog.editing) {
        return updateCustomer(dialog.editing.id, {
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
      dialog.close();
      reset(emptyForm);
      setCreateAddress(emptyAddress);
      setIncludeAddress(false);
      await qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteCustomer(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["customers"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
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

  function openCreate() {
    dialog.openCreate();
    reset(emptyForm);
    setCreateAddress(emptyAddress);
    setIncludeAddress(false);
  }

  function openEdit(item: CustomerResponse) {
    dialog.openEdit(item);
    reset({
      name: item.name,
      document: item.document,
      email: item.email ?? "",
      phone: item.phone ?? "",
      customer_type: item.customer_type,
      ie_indicator: item.ie_indicator,
      is_active: item.is_active,
    });
    setIncludeAddress(false);
  }

  return (
    <RequirePermission module="customers">
      <PageHeader
        title="Clientes"
        description="Cadastro de clientes PF/PJ e endereços."
        actionLabel={canWrite ? "Novo cliente" : undefined}
        onAction={canWrite ? openCreate : undefined}
      />

      <div className="mb-4">
        <Input
          placeholder="Buscar por nome, documento ou e-mail…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </div>

      <ErrorAlert message={dialog.error || (list.error ? errorMessage(list.error) : null)} />

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
                  <TableCell className="text-right">
                    <div className="flex justify-end items-center gap-1">
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
                        <div className="flex gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => openEdit(item)}
                            aria-label="Editar cliente"
                          >
                            <Pencil className="size-3.5" />
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                            onClick={() => {
                              if (confirm(`Excluir cliente "${item.name}"?`)) {
                                remove.mutate(item.id);
                              }
                            }}
                            aria-label="Excluir cliente"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Sheet
        open={dialog.open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) dialog.close();
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>
              {dialog.editing ? "Editar cliente" : "Novo cliente"}
            </SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleSubmit((values) => save.mutate(values))}
            noValidate
            className="flex flex-1 flex-col overflow-y-auto px-4"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="cus-name">Nome</Label>
                <Input id="cus-name" aria-invalid={Boolean(errors.name)} {...register("name")} />
                {errors.name ? (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cus-document">CPF/CNPJ</Label>
                <Input
                  id="cus-document"
                  aria-invalid={Boolean(errors.document)}
                  {...register("document")}
                />
                {errors.document ? (
                  <p className="text-sm text-destructive">{errors.document.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cus-type">Tipo</Label>
                <select
                  id="cus-type"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                  {...register("customer_type")}
                >
                  <option value="F">Pessoa física</option>
                  <option value="J">Pessoa jurídica</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cus-email">E-mail</Label>
                <Input id="cus-email" {...register("email")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cus-phone">Telefone</Label>
                <Input id="cus-phone" {...register("phone")} />
              </div>
              <div className="flex items-center gap-2 self-end text-sm sm:col-span-2">
                <input id="cus-active" type="checkbox" {...register("is_active")} />
                <Label htmlFor="cus-active" className="cursor-pointer font-normal">
                  Ativo
                </Label>
              </div>

              {!dialog.editing ? (
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
                    <AddressFields form={createAddress} onChange={setCreateAddress} />
                  ) : null}
                </div>
              ) : null}
            </div>
            <ErrorAlert message={dialog.error} />
            <SheetFooter className="flex-row justify-end gap-2 border-t border-border px-0">
              <Button type="button" variant="outline" onClick={dialog.close}>
                Cancelar
              </Button>
              <Button
                type="submit"
                disabled={
                  (includeAddress && !addressReady(createAddress)) || save.isPending
                }
              >
                {save.isPending ? "Salvando…" : "Salvar"}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>

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
                            <TableCell className="text-right">
                              <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon-sm"
                                  onClick={() => {
                                    setEditingAddress(addr);
                                    setAddressError(null);
                                  }}
                                  aria-label="Editar endereço"
                                >
                                  <Pencil className="size-3.5" />
                                </Button>
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="icon-sm"
                                  className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                                  onClick={() => {
                                    if (
                                      confirm(
                                        `Excluir endereço "${addr.description}"?`,
                                      )
                                    ) {
                                      removeAddress.mutate(addr.id);
                                    }
                                  }}
                                  aria-label="Excluir endereço"
                                >
                                  <Trash2 className="size-3.5" />
                                </Button>
                              </div>
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
