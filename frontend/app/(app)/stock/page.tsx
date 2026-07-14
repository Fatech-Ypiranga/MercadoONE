"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Button } from "@/components/ui/button";
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
import { listProducts } from "@/lib/api/products-api";
import {
  getStockBalance,
  getStockExtract,
  listStoreBalances,
  moveStock,
} from "@/lib/api/stock-api";
import { errorMessage, formatDateTime, formatNumber } from "@/lib/format";
import { latestDataUpdatedAt, liveQueryOptions } from "@/lib/live-query";

export default function StockPage() {
  const { activeStoreId, activeStore } = useAuth();
  const canWrite = useCan("stock", "write");
  const qc = useQueryClient();
  const [productId, setProductId] = useState("");
  const [qty, setQty] = useState("1");
  const [type, setType] = useState<"E" | "S">("E");
  const [reason, setReason] = useState<"ajuste" | "compra" | "devolucao">("ajuste");
  const [observations, setObservations] = useState("");
  const [error, setError] = useState<string | null>(null);

  const products = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    ...liveQueryOptions,
  });

  const overviewProducts = useMemo(
    () => (products.data ?? []).filter((p) => p.is_active),
    [products.data],
  );

  const overview = useQuery({
    queryKey: [
      "stock",
      "overview",
      activeStoreId,
      overviewProducts.map((p) => p.id).join(","),
    ],
    queryFn: () => listStoreBalances(activeStoreId!, overviewProducts),
    enabled: activeStoreId != null && overviewProducts.length > 0,
    ...liveQueryOptions,
  });

  const selectedId = productId ? Number(productId) : null;

  const balance = useQuery({
    queryKey: ["stock", "balance", selectedId, activeStoreId],
    queryFn: () => getStockBalance(selectedId!, activeStoreId),
    enabled: selectedId != null && activeStoreId != null,
    ...liveQueryOptions,
  });

  const extract = useQuery({
    queryKey: ["stock", "extract", selectedId, activeStoreId],
    queryFn: () => getStockExtract(selectedId!, activeStoreId),
    enabled: selectedId != null && activeStoreId != null,
    ...liveQueryOptions,
  });

  const isFetching =
    products.isFetching ||
    overview.isFetching ||
    balance.isFetching ||
    extract.isFetching;
  const dataUpdatedAt = latestDataUpdatedAt(
    products.dataUpdatedAt,
    overview.dataUpdatedAt,
    balance.dataUpdatedAt,
    extract.dataUpdatedAt,
  );

  const move = useMutation({
    mutationFn: () =>
      moveStock({
        product_id: selectedId!,
        quantity: qty,
        type,
        reason,
        observations: observations.trim() || null,
        store_id: activeStoreId,
      }),
    onSuccess: async () => {
      setError(null);
      setObservations("");
      await qc.invalidateQueries({ queryKey: ["stock"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  return (
    <RequirePermission module="stock">
      <PageHeader
        title="Estoque"
        description={
          activeStore
            ? `Saldo e movimentações da loja ${activeStore.name}.`
            : "Selecione uma loja no header."
        }
        trailing={
          <RefreshControls
            dataUpdatedAt={dataUpdatedAt}
            isFetching={isFetching}
            onRefresh={() => {
              void products.refetch();
              void overview.refetch();
              void balance.refetch();
              void extract.refetch();
            }}
          />
        }
      />

      <ErrorAlert
        message={
          error ||
          (products.error ? errorMessage(products.error) : null) ||
          (overview.error ? errorMessage(overview.error) : null) ||
          (balance.error ? errorMessage(balance.error) : null)
        }
      />

      {!activeStoreId ? (
        <EmptyState message="Selecione uma loja no header para consultar o estoque." />
      ) : (
        <div className="space-y-6">
          <section>
            <h2 className="mb-3 text-sm font-semibold">
              Visão geral da loja (produto × saldo)
            </h2>
            {products.isLoading || overview.isLoading ? (
              <LoadingState message="Carregando saldos da loja…" />
            ) : !overviewProducts.length ? (
              <EmptyState message="Nenhum produto ativo no catálogo." />
            ) : !overview.data?.length ? (
              <EmptyState message="Sem saldos para exibir." />
            ) : (
              <div className="rounded-xl border border-border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>SKU</TableHead>
                      <TableHead>Produto</TableHead>
                      <TableHead className="text-right">Saldo</TableHead>
                      <TableHead className="text-right">Ação</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {overview.data.map((row) => (
                      <TableRow key={row.product_id}>
                        <TableCell className="font-mono text-xs">{row.sku}</TableCell>
                        <TableCell>{row.name}</TableCell>
                        <TableCell className="text-right">
                          {formatNumber(row.current_balance, 3)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => setProductId(String(row.product_id))}
                          >
                            Detalhe
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </section>

          <div className="grid max-w-xl gap-3 rounded-xl border border-border p-4">
            <h2 className="text-sm font-semibold">Movimentação / extrato</h2>
            <div className="space-y-1.5">
              <Label>Produto</Label>
              <select
                className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
              >
                <option value="">Selecione…</option>
                {products.data?.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.sku} — {p.name}
                  </option>
                ))}
              </select>
            </div>

            {selectedId ? (
              <p className="text-sm">
                Saldo atual:{" "}
                <strong>
                  {balance.isLoading
                    ? "…"
                    : formatNumber(balance.data?.current_balance, 3)}
                </strong>
              </p>
            ) : null}

            {canWrite && selectedId ? (
              <div className="grid gap-3 border-t border-border pt-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label>Tipo</Label>
                  <select
                    className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                    value={type}
                    onChange={(e) => setType(e.target.value as "E" | "S")}
                  >
                    <option value="E">Entrada</option>
                    <option value="S">Saída</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label>Motivo</Label>
                  <select
                    className="h-8 w-full rounded-lg border border-input bg-transparent px-2 text-sm"
                    value={reason}
                    onChange={(e) =>
                      setReason(e.target.value as typeof reason)
                    }
                  >
                    <option value="ajuste">Ajuste</option>
                    <option value="compra">Compra</option>
                    <option value="devolucao">Devolução</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <Label>Quantidade</Label>
                  <Input
                    type="number"
                    min="0.001"
                    step="0.001"
                    value={qty}
                    onChange={(e) => setQty(e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label>Observações</Label>
                  <Input
                    value={observations}
                    onChange={(e) => setObservations(e.target.value)}
                  />
                </div>
                <div className="sm:col-span-2">
                  <Button
                    type="button"
                    disabled={!qty || Number(qty) <= 0 || move.isPending}
                    onClick={() => move.mutate()}
                  >
                    {move.isPending ? "Registrando…" : "Registrar movimentação"}
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

          {selectedId ? (
            <section>
              <h2 className="mb-3 text-sm font-semibold">Extrato</h2>
              {extract.isLoading ? (
                <LoadingState />
              ) : !extract.data?.length ? (
                <EmptyState message="Sem movimentações para este produto na loja." />
              ) : (
                <div className="rounded-xl border border-border">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Data</TableHead>
                        <TableHead>Tipo</TableHead>
                        <TableHead>Motivo</TableHead>
                        <TableHead className="text-right">Qtd</TableHead>
                        <TableHead>Obs.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {extract.data.map((m) => (
                        <TableRow key={m.id}>
                          <TableCell>{formatDateTime(m.created_at)}</TableCell>
                          <TableCell>{m.type === "E" ? "Entrada" : "Saída"}</TableCell>
                          <TableCell>{m.reason}</TableCell>
                          <TableCell className="text-right">
                            {formatNumber(m.quantity, 3)}
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {m.observations || "—"}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </section>
          ) : null}
        </div>
      )}
    </RequirePermission>
  );
}
