"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useCan } from "@/hooks/use-can";
import { listProducts } from "@/lib/api/products-api";
import { cancelSale, getSale } from "@/lib/api/sales-api";
import { errorMessage, formatDateTime, formatMoney, formatNumber } from "@/lib/format";

export default function SaleDetailPage() {
  const params = useParams<{ id: string }>();
  const saleId = Number(params.id);
  const { stores } = useAuth();
  const canCancel = useCan("sales", "cancel");
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ["sales", saleId],
    queryFn: () => getSale(saleId),
    enabled: Number.isFinite(saleId),
  });

  const products = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
  });

  const productById = useMemo(() => {
    const map = new Map<number, { sku: string; name: string }>();
    for (const product of products.data ?? []) {
      map.set(product.id, { sku: product.sku, name: product.name });
    }
    return map;
  }, [products.data]);

  const storeName = useMemo(() => {
    const storeId = detail.data?.store_id;
    if (storeId == null) return null;
    return stores.find((store) => store.id === storeId)?.name ?? null;
  }, [detail.data?.store_id, stores]);

  const cancelMutation = useMutation({
    mutationFn: () => cancelSale(saleId),
    onSuccess: () => {
      setError(null);
      void qc.invalidateQueries({ queryKey: ["sales"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const status = detail.data?.status;
  const canCancelThis =
    canCancel && status != null && status !== "Cancelada";

  return (
    <RequirePermission module="sales">
      <PageHeader
        title={detail.data ? `Venda #${detail.data.id}` : "Detalhe da venda"}
        description="Consulta de venda registrada via API (caixa físico fica no app PDV externo)."
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Link
          href="/sales"
          className="inline-flex h-8 items-center rounded-lg border border-border px-3 text-sm hover:bg-muted"
        >
          Voltar
        </Link>
        {canCancelThis ? (
          <Button
            variant="destructive"
            size="sm"
            disabled={cancelMutation.isPending}
            onClick={() => {
              if (
                window.confirm(
                  `Cancelar a venda #${saleId}? O estoque será recomposto.`,
                )
              ) {
                cancelMutation.mutate();
              }
            }}
          >
            {cancelMutation.isPending ? "Cancelando…" : "Cancelar venda"}
          </Button>
        ) : null}
      </div>

      <ErrorAlert
        message={
          error ?? (detail.error ? errorMessage(detail.error) : null)
        }
      />

      {detail.isLoading ? (
        <LoadingState />
      ) : !detail.data ? (
        <EmptyState message="Venda não encontrada." />
      ) : (
        <div className="space-y-6">
          <dl className="grid gap-4 rounded-xl border border-border p-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Data</dt>
              <dd className="mt-1 text-sm">
                {formatDateTime(detail.data.sale_date)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Status</dt>
              <dd className="mt-1">
                <Badge>{detail.data.status}</Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Pagamento</dt>
              <dd className="mt-1 text-sm">
                {detail.data.payment_method ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Total</dt>
              <dd className="mt-1 text-sm font-semibold">
                {formatMoney(detail.data.total_amount)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Loja</dt>
              <dd className="mt-1 text-sm">
                {storeName ?? `#${detail.data.store_id}`}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Cliente</dt>
              <dd className="mt-1 text-sm">
                {detail.data.customer_id != null
                  ? `#${detail.data.customer_id}`
                  : "—"}
              </dd>
            </div>
          </dl>

          <div className="rounded-xl border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>SKU</TableHead>
                  <TableHead>Produto</TableHead>
                  <TableHead className="text-right">Qtd</TableHead>
                  <TableHead className="text-right">Preço un.</TableHead>
                  <TableHead className="text-right">Subtotal</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.data.items.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-muted-foreground">
                      Nenhum item.
                    </TableCell>
                  </TableRow>
                ) : (
                  detail.data.items.map((item) => {
                    const qty = Number(item.quantity);
                    const unit = Number(item.unit_price);
                    const subtotal =
                      Number.isFinite(qty) && Number.isFinite(unit)
                        ? qty * unit
                        : null;
                    const product = productById.get(item.product_id);
                    return (
                      <TableRow key={item.id}>
                        <TableCell className="font-mono text-xs">
                          {product?.sku ?? `#${item.product_id}`}
                        </TableCell>
                        <TableCell>
                          {product?.name ?? `Produto #${item.product_id}`}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatNumber(item.quantity, 3)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatMoney(item.unit_price)}
                        </TableCell>
                        <TableCell className="text-right">
                          {formatMoney(subtotal)}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </RequirePermission>
  );
}
