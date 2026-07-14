"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listPurchases } from "@/lib/api/purchases-api";
import {
  getAverageTicket,
  getCriticalStock,
  getTopProducts,
} from "@/lib/api/reports-api";
import { listSales } from "@/lib/api/sales-api";
import { errorMessage, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { latestDataUpdatedAt, liveQueryOptions } from "@/lib/live-query";

export default function DashboardPage() {
  const { user, activeStoreId, activeStore } = useAuth();
  const storeQuery = activeStoreId ?? undefined;

  const top = useQuery({
    queryKey: ["reports", "top", storeQuery],
    queryFn: () => getTopProducts({ limit: 5, store_id: storeQuery }),
    ...liveQueryOptions,
  });
  const ticket = useQuery({
    queryKey: ["reports", "ticket", storeQuery],
    queryFn: () => getAverageTicket({ store_id: storeQuery }),
    ...liveQueryOptions,
  });
  const critical = useQuery({
    queryKey: ["reports", "critical", storeQuery],
    queryFn: () => getCriticalStock({ min_threshold: 5, store_id: storeQuery }),
    ...liveQueryOptions,
  });
  const sales = useQuery({
    queryKey: ["sales", "recent", storeQuery],
    queryFn: () => listSales({ store_id: storeQuery }),
    ...liveQueryOptions,
  });
  const purchases = useQuery({
    queryKey: ["purchases", "recent", storeQuery],
    queryFn: () => listPurchases({ store_id: storeQuery }),
    ...liveQueryOptions,
  });

  if (!user) return null;

  const loadError =
    top.error || ticket.error || critical.error || sales.error || purchases.error;
  const isFetching =
    top.isFetching ||
    ticket.isFetching ||
    critical.isFetching ||
    sales.isFetching ||
    purchases.isFetching;
  const dataUpdatedAt = latestDataUpdatedAt(
    top.dataUpdatedAt,
    ticket.dataUpdatedAt,
    critical.dataUpdatedAt,
    sales.dataUpdatedAt,
    purchases.dataUpdatedAt,
  );

  return (
    <RequirePermission module="reports">
      <PageHeader
        title="Dashboard"
        description={
          activeStore
            ? `Visão da loja ${activeStore.name}. Troque a loja no header para filtrar.`
            : "Selecione uma loja no header para filtrar indicadores."
        }
        trailing={
          <RefreshControls
            dataUpdatedAt={dataUpdatedAt}
            isFetching={isFetching}
            onRefresh={() => {
              void top.refetch();
              void ticket.refetch();
              void critical.refetch();
              void sales.refetch();
              void purchases.refetch();
            }}
          />
        }
      />

      <ErrorAlert message={loadError ? errorMessage(loadError) : null} />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Ticket médio"
          value={
            ticket.isLoading
              ? "…"
              : formatMoney(ticket.data?.average_ticket)
          }
        />
        <MetricCard
          label="Itens críticos"
          value={
            critical.isLoading
              ? "…"
              : formatNumber(critical.data?.length ?? 0)
          }
        />
        <MetricCard
          label="Vendas (lista)"
          value={
            sales.isLoading ? "…" : formatNumber(sales.data?.length ?? 0)
          }
        />
        <MetricCard
          label="Compras (lista)"
          value={
            purchases.isLoading
              ? "…"
              : formatNumber(purchases.data?.length ?? 0)
          }
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-border p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Top produtos</h2>
            <Link href="/reports" className="text-xs text-muted-foreground hover:underline">
              Ver relatórios
            </Link>
          </div>
          {top.isLoading ? (
            <LoadingState />
          ) : !top.data?.length ? (
            <EmptyState message="Sem vendas no período/loja." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produto</TableHead>
                  <TableHead className="text-right">Qtd</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {top.data.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.name}</TableCell>
                    <TableCell className="text-right">
                      {formatNumber(item.total_sold, 3)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="rounded-xl border border-border p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Estoque crítico</h2>
            <Link href="/stock" className="text-xs text-muted-foreground hover:underline">
              Ir ao estoque
            </Link>
          </div>
          {critical.isLoading ? (
            <LoadingState />
          ) : !critical.data?.length ? (
            <EmptyState message="Nenhum item abaixo do limiar." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produto</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {critical.data.slice(0, 8).map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.name}</TableCell>
                    <TableCell className="text-right">
                      <Badge variant="destructive">
                        {formatNumber(item.current_stock, 3)}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="rounded-xl border border-border p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Últimas vendas</h2>
            <Link href="/sales" className="text-xs text-muted-foreground hover:underline">
              Ver todas
            </Link>
          </div>
          {sales.isLoading ? (
            <LoadingState />
          ) : !sales.data?.length ? (
            <EmptyState message="Nenhuma venda encontrada." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Data</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sales.data.slice(0, 6).map((sale) => (
                  <TableRow key={sale.id}>
                    <TableCell>{sale.id}</TableCell>
                    <TableCell>{formatDate(sale.sale_date)}</TableCell>
                    <TableCell>{sale.status}</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(sale.total_amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>

        <section className="rounded-xl border border-border p-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Últimas compras</h2>
            <Link href="/purchases" className="text-xs text-muted-foreground hover:underline">
              Ver todas
            </Link>
          </div>
          {purchases.isLoading ? (
            <LoadingState />
          ) : !purchases.data?.length ? (
            <EmptyState message="Nenhuma compra encontrada." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>NF</TableHead>
                  <TableHead>Fornecedor</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {purchases.data.slice(0, 6).map((po) => (
                  <TableRow key={po.id}>
                    <TableCell>{po.invoice_number ?? po.id}</TableCell>
                    <TableCell>{po.supplier_name ?? po.supplier_id}</TableCell>
                    <TableCell>{po.status}</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(po.total_amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </section>
      </div>
    </RequirePermission>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border p-4">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        {label}
      </p>
      <p className="mt-2 text-2xl font-semibold tracking-tight">{value}</p>
    </div>
  );
}
