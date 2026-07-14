"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCan } from "@/hooks/use-can";
import { listCategories } from "@/lib/api/categories-api";
import { listProducts } from "@/lib/api/products-api";
import {
  cancelPurchase,
  confirmPurchase,
  listPurchases,
  uploadPurchaseXml,
  type NfeUploadPreviewResponse,
  type PurchaseConfirmRequest,
} from "@/lib/api/purchases-api";
import { errorMessage, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-query";

type ItemMapping = {
  product_id: string;
  create_new: boolean;
  new_sku: string;
  category_id: string;
};

export default function PurchasesPage() {
  const { activeStoreId, activeStore } = useAuth();
  const canWrite = useCan("purchases", "write");
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [preview, setPreview] = useState<NfeUploadPreviewResponse | null>(null);
  const [mappings, setMappings] = useState<Record<number, ItemMapping>>({});

  const list = useQuery({
    queryKey: ["purchases", activeStoreId, status],
    queryFn: () =>
      listPurchases({
        store_id: activeStoreId ?? undefined,
        status: status || undefined,
      }),
    ...liveQueryOptions,
  });

  const products = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    enabled: Boolean(preview),
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
    enabled: Boolean(preview),
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadPurchaseXml(file),
    onSuccess: (data) => {
      setError(null);
      setPreview(data);
      const initial: Record<number, ItemMapping> = {};
      data.items.forEach((item) => {
        initial[item.line_number] = {
          product_id: item.suggested_product_id
            ? String(item.suggested_product_id)
            : "",
          create_new: item.mapping_status === "unmapped",
          new_sku: `${item.supplier_product_code}`.slice(0, 40),
          category_id: categories.data?.[0]
            ? String(categories.data[0].id)
            : "",
        };
      });
      setMappings(initial);
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const confirmMutation = useMutation({
    mutationFn: async () => {
      if (!preview) throw new Error("Sem preview");
      if (!activeStoreId) throw new Error("Selecione uma loja no header");

      const body: PurchaseConfirmRequest = {
        access_key: preview.invoice.access_key,
        invoice_number: preview.invoice.invoice_number,
        invoice_series: preview.invoice.invoice_series,
        issue_date: preview.invoice.issue_date,
        supplier_id: preview.supplier.supplier_id ?? null,
        create_supplier: !preview.supplier.exists_in_database,
        supplier_name: preview.supplier.name,
        supplier_trade_name: preview.supplier.trade_name ?? null,
        supplier_document: preview.supplier.document,
        supplier_state_registration: preview.supplier.state_registration ?? null,
        store_id: activeStoreId,
        items: preview.items.map((item) => {
          const map = mappings[item.line_number];
          const base = {
            supplier_product_code: item.supplier_product_code,
            quantity: item.quantity,
            unit_cost: item.unit_cost,
            discount: item.discount,
            ipi_amount: item.ipi_amount,
            icms_st_amount: item.icms_st_amount,
            total_cost: item.total_cost,
          };
          if (map?.create_new) {
            return {
              ...base,
              product_id: null,
              create_product: {
                name: item.name,
                sku: map.new_sku || item.supplier_product_code,
                barcode: item.barcode ?? null,
                category_id: Number(map.category_id),
                cost_price: item.entry_unit_cost,
                sale_price: item.entry_unit_cost,
                unit_of_measure: item.unit === "KG" ? "KG" : item.unit === "CX" ? "CX" : "UN",
                ncm: item.ncm || null,
              },
            };
          }
          return {
            ...base,
            product_id: Number(map?.product_id || item.suggested_product_id),
            create_product: null,
          };
        }),
      };
      return confirmPurchase(body);
    },
    onSuccess: async () => {
      setPreview(null);
      setMappings({});
      setError(null);
      await qc.invalidateQueries({ queryKey: ["purchases"] });
      await qc.invalidateQueries({ queryKey: ["products"] });
      await qc.invalidateQueries({ queryKey: ["stock"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => cancelPurchase(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["purchases"] });
      await qc.invalidateQueries({ queryKey: ["stock"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const unmappedReady = useMemo(() => {
    if (!preview) return true;
    return preview.items.every((item) => {
      const map = mappings[item.line_number];
      if (!map) return false;
      if (map.create_new) return Boolean(map.category_id && map.new_sku);
      return Boolean(map.product_id || item.suggested_product_id);
    });
  }, [preview, mappings]);

  return (
    <RequirePermission module="purchases">
      <PageHeader
        title="Compras"
        description={
          activeStore
            ? `Entradas da loja ${activeStore.name} via XML NF-e.`
            : "Selecione uma loja no header para confirmar entradas."
        }
        trailing={
          <RefreshControls
            dataUpdatedAt={list.dataUpdatedAt}
            isFetching={list.isFetching}
            onRefresh={() => {
              void list.refetch();
            }}
          />
        }
      />

      <ErrorAlert message={error || (list.error ? errorMessage(list.error) : null)} />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">Todos os status</option>
          <option value="Confirmado">Confirmado</option>
          <option value="Cancelado">Cancelado</option>
          <option value="Rascunho">Rascunho</option>
        </select>

        {canWrite ? (
          <label className="inline-flex h-8 cursor-pointer items-center rounded-lg border border-border px-3 text-sm hover:bg-muted">
            Importar XML
            <input
              type="file"
              accept=".xml,application/xml,text/xml"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) upload.mutate(file);
                e.target.value = "";
              }}
            />
          </label>
        ) : null}
        {upload.isPending ? (
          <span className="text-sm text-muted-foreground">Lendo XML…</span>
        ) : null}
      </div>

      {preview ? (
        <section className="mb-8 space-y-4 rounded-xl border border-border p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold">Preview da NF-e</h2>
              <p className="text-sm text-muted-foreground">
                {preview.supplier.name} · NF {preview.invoice.invoice_number}/
                {preview.invoice.invoice_series} ·{" "}
                {formatMoney(preview.invoice.total_amount)}
              </p>
              <p className="text-xs text-muted-foreground">
                Fornecedor{" "}
                {preview.supplier.exists_in_database
                  ? `já cadastrado (#${preview.supplier.supplier_id})`
                  : "será criado na confirmação"}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setPreview(null);
                  setMappings({});
                }}
              >
                Descartar
              </Button>
              <Button
                type="button"
                disabled={!unmappedReady || !activeStoreId || confirmMutation.isPending}
                onClick={() => confirmMutation.mutate()}
              >
                {confirmMutation.isPending ? "Confirmando…" : "Confirmar entrada"}
              </Button>
            </div>
          </div>

          {!activeStoreId ? (
            <ErrorAlert message="Selecione uma loja no header antes de confirmar." />
          ) : null}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Item</TableHead>
                <TableHead>Qtd</TableHead>
                <TableHead>Custo</TableHead>
                <TableHead>Mapeamento</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {preview.items.map((item) => {
                const map = mappings[item.line_number] ?? {
                  product_id: "",
                  create_new: item.mapping_status === "unmapped",
                  new_sku: item.supplier_product_code,
                  category_id: "",
                };
                return (
                  <TableRow key={item.line_number}>
                    <TableCell>{item.line_number}</TableCell>
                    <TableCell>
                      <div className="font-medium">{item.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {item.supplier_product_code}
                        {item.mapping_status === "mapped" ? (
                          <Badge className="ml-2" variant="secondary">
                            mapeado
                          </Badge>
                        ) : (
                          <Badge className="ml-2" variant="destructive">
                            sem mapa
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{formatNumber(item.quantity, 3)}</TableCell>
                    <TableCell>{formatMoney(item.entry_unit_cost)}</TableCell>
                    <TableCell className="min-w-56 space-y-2">
                      <label className="flex items-center gap-2 text-xs">
                        <input
                          type="checkbox"
                          checked={map.create_new}
                          onChange={(e) =>
                            setMappings((prev) => ({
                              ...prev,
                              [item.line_number]: {
                                ...map,
                                create_new: e.target.checked,
                              },
                            }))
                          }
                        />
                        Criar produto novo
                      </label>
                      {map.create_new ? (
                        <div className="space-y-1">
                          <Input
                            placeholder="SKU"
                            value={map.new_sku}
                            onChange={(e) =>
                              setMappings((prev) => ({
                                ...prev,
                                [item.line_number]: {
                                  ...map,
                                  new_sku: e.target.value,
                                },
                              }))
                            }
                          />
                          <select
                            className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                            value={map.category_id}
                            onChange={(e) =>
                              setMappings((prev) => ({
                                ...prev,
                                [item.line_number]: {
                                  ...map,
                                  category_id: e.target.value,
                                },
                              }))
                            }
                          >
                            <option value="">Categoria…</option>
                            {categories.data?.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name}
                              </option>
                            ))}
                          </select>
                        </div>
                      ) : (
                        <select
                          className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                          value={map.product_id}
                          onChange={(e) =>
                            setMappings((prev) => ({
                              ...prev,
                              [item.line_number]: {
                                ...map,
                                product_id: e.target.value,
                                create_new: false,
                              },
                            }))
                          }
                        >
                          <option value="">Produto…</option>
                          {products.data?.map((p) => (
                            <option key={p.id} value={p.id}>
                              {p.sku} — {p.name}
                            </option>
                          ))}
                        </select>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </section>
      ) : null}

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhuma compra encontrada." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>NF</TableHead>
                <TableHead>Fornecedor</TableHead>
                <TableHead>Emissão</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Total</TableHead>
                {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((po) => (
                <TableRow key={po.id}>
                  <TableCell>
                    <Link
                      href={`/purchases/${po.id}`}
                      className="font-medium hover:underline"
                    >
                      {po.invoice_number ?? `#${po.id}`}
                    </Link>
                    {po.invoice_series ? (
                      <span className="text-muted-foreground">
                        /{po.invoice_series}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell>{po.supplier_name ?? po.supplier_id}</TableCell>
                  <TableCell>{formatDate(po.issue_date)}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        po.status === "Cancelado" ? "secondary" : "default"
                      }
                    >
                      {po.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(po.total_amount)}
                  </TableCell>
                  {canWrite ? (
                    <TableCell className="text-right">
                      {po.status === "Confirmado" ? (
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={() => {
                            if (window.confirm("Cancelar esta compra e estornar estoque?")) {
                              cancelMutation.mutate(po.id);
                            }
                          }}
                        >
                          Cancelar
                        </Button>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </RequirePermission>
  );
}
