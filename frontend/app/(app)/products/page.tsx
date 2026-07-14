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
  cost_price: string;
  sale_price: string;
  category_id: string;
  brand_id: string;
  unit_of_measure: "UN" | "KG" | "CX";
  is_active: boolean;
};

const emptyForm: FormState = {
  name: "",
  sku: "",
  barcode: "",
  cost_price: "0",
  sale_price: "0",
  category_id: "",
  brand_id: "",
  unit_of_measure: "UN",
  is_active: true,
};

export default function ProductsPage() {
  const canWrite = useCan("products", "write");
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<ProductResponse | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const products = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    ...liveQueryOptions,
  });
  const categories = useQuery({ queryKey: ["categories"], queryFn: listCategories });
  const brands = useQuery({ queryKey: ["brands"], queryFn: listBrands });

  const categoryMap = useMemo(() => {
    const map = new Map<number, string>();
    categories.data?.forEach((c) => map.set(c.id, c.name));
    return map;
  }, [categories.data]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return products.data ?? [];
    return (products.data ?? []).filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.sku.toLowerCase().includes(q) ||
        (p.barcode ?? "").toLowerCase().includes(q),
    );
  }, [products.data, search]);

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name.trim(),
        sku: form.sku.trim(),
        barcode: form.barcode.trim() || null,
        cost_price: form.cost_price || "0",
        sale_price: form.sale_price || "0",
        weight_net: "0",
        weight_gross: "0",
        category_id: Number(form.category_id),
        brand_id: form.brand_id ? Number(form.brand_id) : null,
        unit_of_measure: form.unit_of_measure,
        is_active: form.is_active,
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

  function openEdit(item: ProductResponse) {
    setEditing(item);
    setForm({
      name: item.name,
      sku: item.sku,
      barcode: item.barcode ?? "",
      cost_price: String(item.cost_price),
      sale_price: String(item.sale_price),
      category_id: String(item.category_id),
      brand_id: item.brand_id ? String(item.brand_id) : "",
      unit_of_measure: item.unit_of_measure,
      is_active: item.is_active,
    });
    setError(null);
    setOpen(true);
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
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </div>

      <ErrorAlert
        message={error || (products.error ? errorMessage(products.error) : null)}
      />

      {products.isLoading ? (
        <LoadingState />
      ) : !filtered.length ? (
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
              {filtered.map((item) => (
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
                        onClick={() => openEdit(item)}
                      >
                        Editar
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
