"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
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
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCan } from "@/hooks/use-can";
import { listBrands } from "@/lib/api/brands-api";
import { listCategories } from "@/lib/api/categories-api";
import {
  createProduct,
  deleteProduct,
  getProduct,
  listProducts,
  updateProduct,
  type ProductResponse,
} from "@/lib/api/products-api";
import { errorMessage, formatMoney } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-query";

type FormState = {
  name: string;
  sku: string;
  barcode: string;
  description: string;
  cost_price: string;
  sale_price: string;
  weight_net: string;
  weight_gross: string;
  category_id: string;
  brand_id: string;
  unit_of_measure: "UN" | "KG" | "CX";
  is_active: boolean;
  ncm: string;
  cest: string;
  cfop_default: string;
  origem_produto: string;
};

const emptyForm: FormState = {
  name: "",
  sku: "",
  barcode: "",
  description: "",
  cost_price: "0",
  sale_price: "0",
  weight_net: "",
  weight_gross: "",
  category_id: "",
  brand_id: "",
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
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ProductResponse | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [loadingProductId, setLoadingProductId] = useState<number | null>(null);

  const products = useQuery({
    queryKey: ["products", search, offset, PAGE_SIZE],
    queryFn: () =>
      listProducts({
        q: search.trim() || undefined,
        offset,
        limit: PAGE_SIZE,
      }),
    ...liveQueryOptions,
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });
  const brands = useQuery({ queryKey: ["brands"], queryFn: listBrands });

  const categoryMap = useMemo(() => {
    const map = new Map<number, string>();
    categories.data?.forEach((c) => map.set(c.id, c.name));
    return map;
  }, [categories.data]);

  const save = useMutation({
    mutationFn: async () => {
      const hasFiscal = Boolean(
        form.ncm.trim() ||
          form.cest.trim() ||
          form.cfop_default.trim() ||
          form.origem_produto.trim(),
      );
      const payload = {
        name: form.name.trim(),
        sku: form.sku.trim(),
        barcode: form.barcode.trim() || null,
        description: form.description.trim() || null,
        cost_price: form.cost_price || "0",
        sale_price: form.sale_price || "0",
        weight_net: form.weight_net || null,
        weight_gross: form.weight_gross || null,
        category_id: Number(form.category_id),
        brand_id: form.brand_id ? Number(form.brand_id) : null,
        unit_of_measure: form.unit_of_measure,
        is_active: form.is_active,
        fiscal: hasFiscal
          ? {
              ncm: form.ncm.trim(),
              cest: form.cest.trim() || null,
              cfop_default: form.cfop_default.trim(),
              origem_produto: Number(form.origem_produto),
            }
          : null,
      };
      if (editing) return updateProduct(editing.id, payload);
      return createProduct(payload);
    },
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteProduct(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["products"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  function openCreate() {
    setEditing(null);
    setForm({
      ...emptyForm,
      category_id: categories.data?.[0] ? String(categories.data[0].id) : "",
    });
    setError(null);
    setOpen(true);
  }

  async function openEdit(item: ProductResponse) {
    setLoadingProductId(item.id);
    setError(null);
    try {
      const detail = await getProduct(item.id);
      setEditing(detail);
      setForm({
        name: detail.name,
        sku: detail.sku,
        barcode: detail.barcode ?? "",
        description: detail.description ?? "",
        cost_price: String(detail.cost_price),
        sale_price: String(detail.sale_price),
        weight_net: detail.weight_net == null ? "" : String(detail.weight_net),
        weight_gross: detail.weight_gross == null ? "" : String(detail.weight_gross),
        category_id: String(detail.category_id),
        brand_id: detail.brand_id ? String(detail.brand_id) : "",
        unit_of_measure: detail.unit_of_measure,
        is_active: detail.is_active,
        ncm: detail.fiscal?.ncm ?? "",
        cest: detail.fiscal?.cest ?? "",
        cfop_default: detail.fiscal?.cfop_default ?? "",
        origem_produto:
          detail.fiscal?.origem_produto == null
            ? ""
            : String(detail.fiscal.origem_produto),
      });
      setOpen(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingProductId(null);
    }
  }

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

      <div className="mb-4">
        <Input
          placeholder="Buscar por nome, SKU ou código de barras…"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
          className="max-w-md"
        />
      </div>

      <ErrorAlert
        message={error || (products.error ? errorMessage(products.error) : null)}
      />

      {products.isLoading ? (
        <LoadingState />
      ) : !products.data?.length ? (
        <EmptyState message="Nenhum produto encontrado." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead>Nome</TableHead>
                <TableHead>Categoria</TableHead>
                <TableHead className="text-right">Custo</TableHead>
                <TableHead className="text-right">Venda</TableHead>
                <TableHead>Status</TableHead>
                {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {products.data.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-mono text-xs">{item.sku}</TableCell>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell>
                    {categoryMap.get(item.category_id) ?? item.category_id}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(item.cost_price)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(item.sale_price)}
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
                        disabled={loadingProductId === item.id}
                        onClick={() => void openEdit(item)}
                      >
                        {loadingProductId === item.id ? "Carregando…" : "Editar"}
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Excluir produto "${item.name}"?`)) {
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

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? "Editar produto" : "Novo produto"}
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
              <Label>SKU</Label>
              <Input
                value={form.sku}
                onChange={(e) => setForm((p) => ({ ...p, sku: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Código de barras</Label>
              <Input
                value={form.barcode}
                onChange={(e) => setForm((p) => ({ ...p, barcode: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Descrição</Label>
              <Textarea
                value={form.description}
                onChange={(e) =>
                  setForm((p) => ({ ...p, description: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Preço de custo</Label>
              <Input
                type="number"
                step="0.01"
                value={form.cost_price}
                onChange={(e) =>
                  setForm((p) => ({ ...p, cost_price: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Peso líquido</Label>
              <Input
                type="number"
                min="0"
                step="0.001"
                value={form.weight_net}
                onChange={(e) =>
                  setForm((p) => ({ ...p, weight_net: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Peso bruto</Label>
              <Input
                type="number"
                min="0"
                step="0.001"
                value={form.weight_gross}
                onChange={(e) =>
                  setForm((p) => ({ ...p, weight_gross: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Preço de venda</Label>
              <Input
                type="number"
                step="0.01"
                value={form.sale_price}
                onChange={(e) =>
                  setForm((p) => ({ ...p, sale_price: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Categoria</Label>
              <select
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                value={form.category_id}
                onChange={(e) =>
                  setForm((p) => ({ ...p, category_id: e.target.value }))
                }
              >
                <option value="">Selecione…</option>
                {categories.data?.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Marca</Label>
              <select
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                value={form.brand_id}
                onChange={(e) =>
                  setForm((p) => ({ ...p, brand_id: e.target.value }))
                }
              >
                <option value="">—</option>
                {brands.data?.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Unidade</Label>
              <select
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                value={form.unit_of_measure}
                onChange={(e) =>
                  setForm((p) => ({
                    ...p,
                    unit_of_measure: e.target.value as FormState["unit_of_measure"],
                  }))
                }
              >
                <option value="UN">UN</option>
                <option value="KG">KG</option>
                <option value="CX">CX</option>
              </select>
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
            <div className="sm:col-span-2 mt-2 border-t border-border pt-3">
              <p className="text-sm font-medium">Dados fiscais (opcional)</p>
              <p className="text-xs text-muted-foreground">
                Ao preencher, informe NCM, CFOP e origem.
              </p>
            </div>
            <div className="space-y-1.5">
              <Label>NCM</Label>
              <Input
                inputMode="numeric"
                maxLength={8}
                value={form.ncm}
                onChange={(e) => setForm((p) => ({ ...p, ncm: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>CEST</Label>
              <Input
                inputMode="numeric"
                maxLength={7}
                value={form.cest}
                onChange={(e) => setForm((p) => ({ ...p, cest: e.target.value }))}
              />
            </div>
            <div className="space-y-1.5">
              <Label>CFOP padrão</Label>
              <Input
                inputMode="numeric"
                maxLength={4}
                value={form.cfop_default}
                onChange={(e) =>
                  setForm((p) => ({ ...p, cfop_default: e.target.value }))
                }
              />
            </div>
            <div className="space-y-1.5">
              <Label>Origem do produto</Label>
              <select
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                value={form.origem_produto}
                onChange={(e) =>
                  setForm((p) => ({ ...p, origem_produto: e.target.value }))
                }
              >
                <option value="">Selecione…</option>
                {Array.from({ length: 9 }, (_, value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </div>
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
                !form.sku.trim() ||
                !form.category_id ||
                (Boolean(
                  form.ncm.trim() ||
                    form.cest.trim() ||
                    form.cfop_default.trim() ||
                    form.origem_produto.trim(),
                ) &&
                  (!form.ncm.trim() ||
                    !form.cfop_default.trim() ||
                    !form.origem_produto.trim())) ||
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
