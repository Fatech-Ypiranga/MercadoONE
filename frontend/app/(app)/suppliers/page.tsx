"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createColumnHelper,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table";
import { Pencil, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import {
  AddressFields,
  addressPayload,
  addressReady,
  emptyAddress,
} from "@/components/address-fields";
import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DataTable } from "@/components/ui/data-table";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useCan } from "@/hooks/use-can";
import { useEntityDialog } from "@/hooks/use-entity-dialog";
import {
  createSupplier,
  deleteSupplier,
  listSuppliers,
  updateSupplier,
  type SupplierResponse,
} from "@/lib/api/suppliers-api";
import { errorMessage } from "@/lib/format";

const addressSchema = z
  .object({
    description: z.string(),
    zip_code: z.string(),
    street: z.string(),
    number: z.string(),
    complement: z.string(),
    neighborhood: z.string(),
    city: z.string(),
    state: z.string(),
    ibge_code: z.string(),
  })
  .refine((address) => addressReady(address), {
    message: "Endereço incompleto: informe CEP, rua, número, bairro, cidade e UF",
  });

const supplierSchema = z.object({
  name: z.string().trim().min(1, "Informe a razão social"),
  trade_name: z.string(),
  document: z.string().refine((v) => v.replace(/\D/g, "").length > 0, "Informe o CNPJ"),
  state_registration: z.string(),
  email: z.string(),
  phone: z.string(),
  is_active: z.boolean(),
  address: addressSchema,
});

type SupplierForm = z.infer<typeof supplierSchema>;

const emptyForm: SupplierForm = {
  name: "",
  trade_name: "",
  document: "",
  state_registration: "",
  email: "",
  phone: "",
  is_active: true,
  address: emptyAddress,
};

export default function SuppliersPage() {
  const canWrite = useCan("suppliers", "write");
  const qc = useQueryClient();
  const dialog = useEntityDialog<SupplierResponse>();
  const [search, setSearch] = useState("");
  const trimmedSearch = search.trim();
  const searchDigits = trimmedSearch.replace(/\D/g, "");
  const searchableCharacters = trimmedSearch.replace(/\s/g, "").length;
  const searchByCode = searchDigits.length === 8 && searchDigits === trimmedSearch;
  const searchByDocument =
    !searchByCode &&
    searchDigits.length > 0 &&
    searchDigits.length >= searchableCharacters / 2;

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<SupplierForm>({
    resolver: zodResolver(supplierSchema),
    defaultValues: emptyForm,
  });
  const address = watch("address");

  const list = useQuery({
    queryKey: ["suppliers", search],
    queryFn: () =>
      listSuppliers({
        name:
          trimmedSearch && !searchByDocument && !searchByCode ? trimmedSearch : undefined,
        document: trimmedSearch && searchByDocument ? searchDigits : undefined,
        code: searchByCode ? searchDigits : undefined,
      }),
  });

  const save = useMutation({
    mutationFn: async (values: SupplierForm) => {
      const payload = {
        name: values.name,
        trade_name: values.trade_name.trim() || null,
        document: values.document.replace(/\D/g, ""),
        state_registration: values.state_registration.trim() || null,
        email: values.email.trim() || null,
        phone: values.phone.trim() || null,
        is_active: values.is_active,
        address: addressPayload(values.address),
      };
      if (dialog.editing) return updateSupplier(dialog.editing.id, payload);
      return createSupplier(payload);
    },
    onSuccess: async () => {
      dialog.close();
      reset(emptyForm);
      await qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteSupplier(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["suppliers"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  function openEdit(item: SupplierResponse) {
    dialog.openEdit(item);
    reset({
      name: item.name,
      trade_name: item.trade_name ?? "",
      document: item.document,
      state_registration: item.state_registration ?? "",
      email: item.email ?? "",
      phone: item.phone ?? "",
      is_active: item.is_active,
      address: item.address
        ? {
            description: item.address.description,
            zip_code: item.address.zip_code,
            street: item.address.street,
            number: item.address.number,
            complement: item.address.complement ?? "",
            neighborhood: item.address.neighborhood,
            city: item.address.city,
            state: item.address.state,
            ibge_code: item.address.ibge_code,
          }
        : emptyAddress,
    });
  }

  function openCreate() {
    dialog.openCreate();
    reset(emptyForm);
  }

  const columns = useMemo(() => {
    const helper = createColumnHelper<SupplierResponse>();
    return [
      helper.accessor((row) => row.code || "—", {
        id: "code",
        header: "Código",
        cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
      }),
      helper.accessor("name", {
        header: "Nome",
        cell: (info) => (
          <div>
            <div className="font-medium">{info.getValue()}</div>
            {info.row.original.trade_name ? (
              <div className="text-xs text-muted-foreground">{info.row.original.trade_name}</div>
            ) : null}
          </div>
        ),
      }),
      helper.accessor("document", {
        header: "CNPJ",
        cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
      }),
      helper.accessor((row) => row.state_registration || "—", {
        id: "ie",
        header: "IE",
        cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
        enableSorting: false,
      }),
      helper.accessor((row) => row.email || row.phone || "—", {
        id: "contact",
        header: "Contato",
        cell: (info) => <span className="text-muted-foreground">{info.getValue()}</span>,
        enableSorting: false,
      }),
      helper.accessor("is_active", {
        header: "Status",
        cell: (info) => (
          <Badge variant={info.getValue() ? "default" : "secondary"}>
            {info.getValue() ? "Ativo" : "Inativo"}
          </Badge>
        ),
        enableSorting: false,
      }),
      ...(canWrite
        ? [
            helper.display({
              id: "actions",
              header: "Ações",
              meta: { align: "right" },
              cell: (info) => {
                const item = info.row.original;
                return (
                  <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => openEdit(item)}
                      aria-label="Editar fornecedor"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => {
                        if (confirm(`Excluir fornecedor "${item.name}"?`)) {
                          remove.mutate(item.id);
                        }
                      }}
                      aria-label="Excluir fornecedor"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                );
              },
            }),
          ]
        : []),
    ];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canWrite]);

  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data: list.data ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <RequirePermission module="suppliers">
      <PageHeader
        title="Fornecedores"
        description="Cadastro de fornecedores para compras."
        actionLabel={canWrite ? "Novo fornecedor" : undefined}
        onAction={canWrite ? openCreate : undefined}
      />

      <div className="mb-4">
        <Input
          placeholder="Buscar por nome, CNPJ ou código…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </div>

      <ErrorAlert message={dialog.error || (list.error ? errorMessage(list.error) : null)} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhum fornecedor encontrado." />
      ) : (
        <div className="rounded-xl border border-border">
          <DataTable table={table} />
        </div>
      )}

      <Sheet
        open={dialog.open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) dialog.close();
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>
              {dialog.editing ? "Editar fornecedor" : "Novo fornecedor"}
            </SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleSubmit((values) => save.mutate(values))}
            noValidate
            className="flex flex-1 flex-col overflow-y-auto px-4"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              {dialog.editing ? (
                <div className="space-y-1.5 sm:col-span-2">
                  <Label>Código</Label>
                  <Input value={dialog.editing.code ?? "Será gerado ao salvar"} readOnly />
                </div>
              ) : null}
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="sup-name">Razão social</Label>
                <Input id="sup-name" aria-invalid={Boolean(errors.name)} {...register("name")} />
                {errors.name ? (
                  <p role="alert" className="text-sm text-destructive">{errors.name.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="sup-trade-name">Nome fantasia</Label>
                <Input id="sup-trade-name" {...register("trade_name")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sup-document">CNPJ</Label>
                <Input
                  id="sup-document"
                  aria-invalid={Boolean(errors.document)}
                  {...register("document")}
                />
                {errors.document ? (
                  <p role="alert" className="text-sm text-destructive">{errors.document.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sup-ie">Inscrição estadual</Label>
                <Input id="sup-ie" {...register("state_registration")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sup-email">E-mail</Label>
                <Input id="sup-email" {...register("email")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sup-phone">Telefone</Label>
                <Input id="sup-phone" {...register("phone")} />
              </div>
              <div className="flex items-center gap-2 self-end text-sm">
                <input id="sup-active" type="checkbox" {...register("is_active")} />
                <Label htmlFor="sup-active" className="cursor-pointer font-normal">
                  Ativo
                </Label>
              </div>
            </div>
            <div className="space-y-3">
              <h3 className="text-sm font-medium">Endereço principal</h3>
              <AddressFields
                form={address}
                onChange={(next) => setValue("address", next, { shouldValidate: true })}
              />
              {errors.address ? (
                <p role="alert" className="text-sm text-destructive">{errors.address.message}</p>
              ) : null}
            </div>
            <ErrorAlert message={dialog.error} />
            <SheetFooter className="flex-row justify-end gap-2 border-t border-border px-0">
              <Button type="button" variant="outline" onClick={dialog.close}>
                Cancelar
              </Button>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Salvando…" : "Salvar"}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>
    </RequirePermission>
  );
}
