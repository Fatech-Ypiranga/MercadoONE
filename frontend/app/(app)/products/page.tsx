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

import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
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
import { Textarea } from "@/components/ui/textarea";
import { useCan } from "@/hooks/use-can";
import { useEntityDialog } from "@/hooks/use-entity-dialog";
import { listCategories } from "@/lib/api/categories-api";
import {
  createProduct,
  deleteProduct,
  getProduct,
  listProducts,
  updateProduct,
  type ProductResponse,
} from "@/lib/api/products-api";
import { listSuppliers } from "@/lib/api/suppliers-api";
import { errorMessage, formatMoney } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-query";

const productSchema = z
  .object({
    name: z.string().trim().min(1, "Informe o nome"),
    sku: z.string().trim().min(1, "Informe o SKU"),
    barcode: z.string(),
    description: z.string(),
    cost_price: z.string(),
    sale_price: z.string(),
    weight_net: z.string(),
    weight_gross: z.string(),
    min_stock: z.string(),
    category_id: z.string().min(1, "Selecione a categoria"),
    primary_supplier_id: z.string().min(1, "Selecione o fornecedor"),
    unit_of_measure: z.enum(["UN", "KG", "CX"]),
    is_active: z.boolean(),
    ncm: z.string(),
    cest: z.string(),
    cfop_default: z.string(),
    origem_produto: z.string(),
  })
  .superRefine((data, ctx) => {
    const hasFiscal = Boolean(
      data.ncm.trim() ||
        data.cest.trim() ||
        data.cfop_default.trim() ||
        data.origem_produto.trim(),
    );
    if (!hasFiscal) return;
    if (!data.ncm.trim()) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["ncm"], message: "Informe o NCM" });
    }
    if (!data.cfop_default.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["cfop_default"],
        message: "Informe o CFOP",
      });
    }
    if (!data.origem_produto.trim()) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["origem_produto"],
        message: "Informe a origem",
      });
    }
  });

type ProductForm = z.infer<typeof productSchema>;

const emptyForm: ProductForm = {
  name: "",
  sku: "",
  barcode: "",
  description: "",
  cost_price: "0",
  sale_price: "0",
  weight_net: "",
  weight_gross: "",
  min_stock: "",
  category_id: "",
  primary_supplier_id: "",
  unit_of_measure: "UN",
  is_active: true,
  ncm: "",
  cest: "",
  cfop_default: "",
  origem_produto: "",
};

const PAGE_SIZE = 50;

export default function ProductsPage() {
  const canWrite = useCan("products", "write");
  const qc = useQueryClient();
  const dialog = useEntityDialog<ProductResponse>();
  const [search, setSearch] = useState("");
  const [supplierFilter, setSupplierFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [loadingProductId, setLoadingProductId] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ProductForm>({
    resolver: zodResolver(productSchema),
    defaultValues: emptyForm,
  });

  const products = useQuery({
    queryKey: ["products", search, supplierFilter, offset, PAGE_SIZE],
    queryFn: () =>
      listProducts({
        q: search.trim() || undefined,
        primary_supplier_id: supplierFilter ? Number(supplierFilter) : undefined,
        offset,
        limit: PAGE_SIZE,
      }),
    ...liveQueryOptions,
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });
  const suppliers = useQuery({ queryKey: ["suppliers"], queryFn: listSuppliers });

  const categoryMap = useMemo(() => {
    const map = new Map<number, string>();
    categories.data?.forEach((c) => map.set(c.id, c.name));
    return map;
  }, [categories.data]);

  const supplierMap = useMemo(() => {
    const map = new Map<number, string>();
    suppliers.data?.forEach((supplier) =>
      map.set(
        supplier.id,
        supplier.code ? `${supplier.code} — ${supplier.name}` : supplier.name,
      ),
    );
    return map;
  }, [suppliers.data]);

  const leafCategories = useMemo(() => {
    const all = categories.data ?? [];
    const childParentIds = new Set(all.filter((c) => c.parent_id != null).map((c) => c.parent_id!));
    return all.filter(
      (c) => c.parent_id != null || !childParentIds.has(c.id),
    );
  }, [categories.data]);

  const categoryLabel = (c: { id: number; name: string; parent_id?: number | null }) => {
    if (c.parent_id != null) {
      const parent = categoryMap.get(c.parent_id);
      return parent ? `${parent} / ${c.name}` : c.name;
    }
    return c.name;
  };

  const save = useMutation({
    mutationFn: async (values: ProductForm) => {
      const hasFiscal = Boolean(
        values.ncm.trim() ||
          values.cest.trim() ||
          values.cfop_default.trim() ||
          values.origem_produto.trim(),
      );
      const payload = {
        name: values.name.trim(),
        sku: values.sku.trim(),
        barcode: values.barcode.trim() || null,
        description: values.description.trim() || null,
        cost_price: values.cost_price || "0",
        sale_price: values.sale_price || "0",
        weight_net: values.weight_net || null,
        weight_gross: values.weight_gross || null,
        min_stock: values.min_stock.trim() || null,
        category_id: Number(values.category_id),
        primary_supplier_id: Number(values.primary_supplier_id),
        unit_of_measure: values.unit_of_measure,
        is_active: values.is_active,
        fiscal: hasFiscal
          ? {
              ncm: values.ncm.trim(),
              cest: values.cest.trim() || null,
              cfop_default: values.cfop_default.trim(),
              origem_produto: Number(values.origem_produto),
            }
          : null,
      };
      if (dialog.editing) return updateProduct(dialog.editing.id, payload);
      return createProduct(payload);
    },
    onSuccess: async () => {
      dialog.close();
      reset(emptyForm);
      await qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  function openCreate() {
    dialog.openCreate();
    reset({
      ...emptyForm,
      category_id: leafCategories[0] ? String(leafCategories[0].id) : "",
      primary_supplier_id: suppliers.data?.[0] ? String(suppliers.data[0].id) : "",
    });
  }

  async function openEdit(item: ProductResponse) {
    setLoadingProductId(item.id);
    try {
      const detail = await getProduct(item.id);
      dialog.openEdit(detail);
      reset({
        name: detail.name,
        sku: detail.sku,
        barcode: detail.barcode ?? "",
        description: detail.description ?? "",
        cost_price: String(detail.cost_price),
        sale_price: String(detail.sale_price),
        weight_net: detail.weight_net == null ? "" : String(detail.weight_net),
        weight_gross: detail.weight_gross == null ? "" : String(detail.weight_gross),
        min_stock: detail.min_stock == null ? "" : String(detail.min_stock),
        category_id: String(detail.category_id),
        primary_supplier_id: detail.primary_supplier_id
          ? String(detail.primary_supplier_id)
          : "",
        unit_of_measure: detail.unit_of_measure,
        is_active: detail.is_active,
        ncm: detail.fiscal?.ncm ?? "",
        cest: detail.fiscal?.cest ?? "",
        cfop_default: detail.fiscal?.cfop_default ?? "",
        origem_produto:
          detail.fiscal?.origem_produto == null ? "" : String(detail.fiscal.origem_produto),
      });
    } catch (err) {
      dialog.setError(errorMessage(err));
    } finally {
      setLoadingProductId(null);
    }
  }

  const columns = useMemo(() => {
    const helper = createColumnHelper<ProductResponse>();
    const cols = [
      helper.accessor("material_code", {
        header: "Material",
        cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
      }),
      helper.accessor("sku", {
        header: "SKU",
        cell: (info) => <span className="font-mono text-xs">{info.getValue()}</span>,
      }),
      helper.accessor("name", {
        header: "Nome",
        cell: (info) => <span className="font-medium">{info.getValue()}</span>,
      }),
      helper.accessor((row) => categoryMap.get(row.category_id) ?? String(row.category_id), {
        id: "category",
        header: "Categoria",
      }),
      helper.accessor(
        (row) =>
          row.primary_supplier_id ? (supplierMap.get(row.primary_supplier_id) ?? "") : "",
        {
          id: "supplier",
          header: "Fornecedor principal",
          cell: (info) =>
            info.row.original.primary_supplier_id ? (
              info.getValue()
            ) : (
              <Badge variant="destructive">Regularização obrigatória</Badge>
            ),
        },
      ),
      helper.accessor((row) => Number(row.cost_price), {
        id: "cost_price",
        header: "Custo",
        cell: (info) => formatMoney(info.getValue()),
        meta: { align: "right" },
      }),
      helper.accessor((row) => Number(row.sale_price), {
        id: "sale_price",
        header: "Venda",
        cell: (info) => formatMoney(info.getValue()),
        meta: { align: "right" },
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
                      disabled={loadingProductId === item.id}
                      onClick={() => void openEdit(item)}
                      aria-label="Editar produto"
                    >
                      <Pencil className="size-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      onClick={() => {
                        if (confirm(`Excluir produto "${item.name}"?`)) {
                          remove.mutate(item.id);
                        }
                      }}
                      aria-label="Excluir produto"
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
    return cols;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canWrite, categoryMap, supplierMap, loadingProductId]);

  const [sorting, setSorting] = useState<SortingState>([]);
  const table = useReactTable({
    data: products.data ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <RequirePermission module="products">
      <PageHeader
        title="Produtos"
        description="Catálogo de produtos da empresa."
        actionLabel={canWrite ? "Novo produto" : undefined}
        onAction={canWrite ? openCreate : undefined}
        trailing={
          <RefreshControls
            dataUpdatedAt={products.dataUpdatedAt}
            isFetching={products.isFetching}
            onRefresh={() => {
              void products.refetch();
            }}
          />
        }
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <Input
          placeholder="Buscar por nome, SKU, código de barras ou material…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="max-w-md"
        />
        <select
          className="h-8 min-w-64 rounded-lg border border-input bg-transparent px-2 text-sm"
          value={supplierFilter}
          onChange={(event) => {
            setSupplierFilter(event.target.value);
            setOffset(0);
          }}
        >
          <option value="">Todos os fornecedores</option>
          {suppliers.data?.map((supplier) => (
            <option key={supplier.id} value={supplier.id}>
              {supplier.code ? `${supplier.code} — ` : ""}
              {supplier.name}
            </option>
          ))}
        </select>
      </div>

      <ErrorAlert
        message={dialog.error || (products.error ? errorMessage(products.error) : null)}
      />

      {products.isLoading ? (
        <LoadingState />
      ) : !products.data?.length ? (
        <EmptyState message="Nenhum produto encontrado." />
      ) : (
        <div className="rounded-xl border border-border">
          <DataTable table={table} />
        </div>
      )}

      <div className="mt-4 flex items-center justify-between">
        <Button
          type="button"
          variant="outline"
          disabled={offset === 0 || products.isFetching}
          onClick={() => setOffset((current) => Math.max(0, current - PAGE_SIZE))}
        >
          Anterior
        </Button>
        <span className="text-sm text-muted-foreground">
          Página {Math.floor(offset / PAGE_SIZE) + 1}
        </span>
        <Button
          type="button"
          variant="outline"
          disabled={(products.data?.length ?? 0) < PAGE_SIZE || products.isFetching}
          onClick={() => setOffset((current) => current + PAGE_SIZE)}
        >
          Próxima
        </Button>
      </div>

      <Sheet
        open={dialog.open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) dialog.close();
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>
              {dialog.editing ? "Editar produto" : "Novo produto"}
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
                  <Label>Código interno de material</Label>
                  <Input value={dialog.editing.material_code} readOnly disabled />
                </div>
              ) : null}
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="prod-name">Nome</Label>
                <Input id="prod-name" aria-invalid={Boolean(errors.name)} {...register("name")} />
                {errors.name ? (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-sku">SKU</Label>
                <Input id="prod-sku" aria-invalid={Boolean(errors.sku)} {...register("sku")} />
                {errors.sku ? (
                  <p className="text-sm text-destructive">{errors.sku.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-barcode">Código de barras</Label>
                <Input id="prod-barcode" {...register("barcode")} />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="prod-description">Descrição</Label>
                <Textarea id="prod-description" {...register("description")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-cost">Preço de custo</Label>
                <Input id="prod-cost" type="number" step="0.01" {...register("cost_price")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-weight-net">Peso líquido</Label>
                <Input
                  id="prod-weight-net"
                  type="number"
                  min="0"
                  step="0.001"
                  {...register("weight_net")}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-weight-gross">Peso bruto</Label>
                <Input
                  id="prod-weight-gross"
                  type="number"
                  min="0"
                  step="0.001"
                  {...register("weight_gross")}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-sale">Preço de venda</Label>
                <Input id="prod-sale" type="number" step="0.01" {...register("sale_price")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-min-stock">Estoque mínimo</Label>
                <Input
                  id="prod-min-stock"
                  type="number"
                  min="0"
                  step="0.001"
                  placeholder="Usar limiar global"
                  {...register("min_stock")}
                />
                <p className="text-xs text-muted-foreground">
                  Vazio usa o limiar global do dashboard (5).
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-category">Categoria</Label>
                <select
                  id="prod-category"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                  aria-invalid={Boolean(errors.category_id)}
                  {...register("category_id")}
                >
                  <option value="">Selecione…</option>
                  {leafCategories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {categoryLabel(c)}
                    </option>
                  ))}
                </select>
                {errors.category_id ? (
                  <p className="text-sm text-destructive">{errors.category_id.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-supplier">Fornecedor principal</Label>
                <select
                  id="prod-supplier"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                  aria-invalid={Boolean(errors.primary_supplier_id)}
                  {...register("primary_supplier_id")}
                >
                  <option value="">Selecione…</option>
                  {suppliers.data?.map((supplier) => (
                    <option key={supplier.id} value={supplier.id}>
                      {supplier.code ? `${supplier.code} — ` : ""}
                      {supplier.name}
                    </option>
                  ))}
                </select>
                {errors.primary_supplier_id ? (
                  <p className="text-sm text-destructive">
                    {errors.primary_supplier_id.message}
                  </p>
                ) : dialog.editing != null && dialog.editing.primary_supplier_id == null ? (
                  <p className="text-xs text-destructive">
                    Produto legado: selecione um fornecedor antes de salvar.
                  </p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-unit">Unidade</Label>
                <select
                  id="prod-unit"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                  {...register("unit_of_measure")}
                >
                  <option value="UN">UN</option>
                  <option value="KG">KG</option>
                  <option value="CX">CX</option>
                </select>
              </div>
              <div className="flex items-center gap-2 self-end text-sm">
                <input id="prod-active" type="checkbox" {...register("is_active")} />
                <Label htmlFor="prod-active" className="cursor-pointer font-normal">
                  Ativo
                </Label>
              </div>
              <div className="sm:col-span-2 mt-2 border-t border-border pt-3">
                <p className="text-sm font-medium">Dados fiscais (opcional)</p>
                <p className="text-xs text-muted-foreground">
                  Ao preencher, informe NCM, CFOP e origem.
                </p>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-ncm">NCM</Label>
                <Input
                  id="prod-ncm"
                  inputMode="numeric"
                  maxLength={8}
                  aria-invalid={Boolean(errors.ncm)}
                  {...register("ncm")}
                />
                {errors.ncm ? (
                  <p className="text-sm text-destructive">{errors.ncm.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-cest">CEST</Label>
                <Input id="prod-cest" inputMode="numeric" maxLength={7} {...register("cest")} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-cfop">CFOP padrão</Label>
                <Input
                  id="prod-cfop"
                  inputMode="numeric"
                  maxLength={4}
                  aria-invalid={Boolean(errors.cfop_default)}
                  {...register("cfop_default")}
                />
                {errors.cfop_default ? (
                  <p className="text-sm text-destructive">{errors.cfop_default.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="prod-origem">Origem do produto</Label>
                <select
                  id="prod-origem"
                  className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                  aria-invalid={Boolean(errors.origem_produto)}
                  {...register("origem_produto")}
                >
                  <option value="">Selecione…</option>
                  {Array.from({ length: 9 }, (_, value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
                {errors.origem_produto ? (
                  <p className="text-sm text-destructive">{errors.origem_produto.message}</p>
                ) : null}
              </div>
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
