"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, type ReactNode } from "react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import {
  DASHBOARD_PERIOD_DAYS,
  DASHBOARD_SALES_LIMIT,
  periodStartIso,
  purchaseStatusBadge,
  saleStatusBadge,
  summarizeSales,
} from "@/lib/dashboard-metrics";
import { errorMessage, formatDate, formatMoney, formatNumber } from "@/lib/format";
import { latestDataUpdatedAt, liveQueryOptions } from "@/lib/live-query";

export default function DashboardPage() {
  const { user, activeStoreId, activeStore } = useAuth();
  const storeQuery = activeStoreId ?? undefined;
  const dateFrom = useMemo(() => periodStartIso(DASHBOARD_PERIOD_DAYS), []);

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
    queryKey: ["sales", "recent", storeQuery, dateFrom],
    queryFn: () =>
      listSales({
        store_id: storeQuery,
        date_from: dateFrom,
        limit: DASHBOARD_SALES_LIMIT,
      }),
    ...liveQueryOptions,
  });
  const purchases = useQuery({
    queryKey: ["purchases", "recent", storeQuery],
    queryFn: () => listPurchases({ store_id: storeQuery, limit: 6 }),
    ...liveQueryOptions,
  });

  const salesSummary = useMemo(
    () => summarizeSales(sales.data ?? []),
    [sales.data],
  );

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

  const periodHint = `Últimos ${DASHBOARD_PERIOD_DAYS} dias`;

  return (
    <RequirePermission module="reports">
      <PageHeader
        title="Dashboard"
        description={
          activeStore
            ? `Visão da loja ${activeStore.name} · ${periodHint.toLowerCase()}. Troque a loja no header para filtrar.`
            : `Selecione uma loja no header para filtrar indicadores · ${periodHint.toLowerCase()}.`
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
          label="Receita"
          hint={periodHint}
          loading={sales.isLoading}
          value={formatMoney(salesSummary.revenue)}
          note={salesSummary.capped ? `Até ${DASHBOARD_SALES_LIMIT} vendas` : undefined}
        />
        <MetricCard
          label="Vendas"
          hint={periodHint}
          loading={sales.isLoading}
          value={formatNumber(salesSummary.count)}
          note={salesSummary.capped ? `Até ${DASHBOARD_SALES_LIMIT} vendas` : undefined}
        />
        <MetricCard
          label="Ticket médio"
          hint="Histórico da loja"
          loading={ticket.isLoading}
          value={formatMoney(ticket.data?.average_ticket)}
        />
        <MetricCard
          label="Estoque crítico"
          hint="Limiar ≥ 5"
          loading={critical.isLoading}
          value={formatNumber(critical.data?.length ?? 0)}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <DashboardPanel
          title="Top produtos"
          actionHref="/reports"
          actionLabel="Ver relatórios"
        >
          {top.isLoading ? (
            <TableSkeleton rows={5} cols={2} />
          ) : !top.data?.length ? (
            <EmptyState
              message="Sem vendas no período/loja."
              actionLabel="Ver relatórios"
              actionHref="/reports"
            />
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
        </DashboardPanel>

        <DashboardPanel
          title="Estoque crítico"
          actionHref="/stock"
          actionLabel="Ir ao estoque"
        >
          {critical.isLoading ? (
            <TableSkeleton rows={5} cols={3} />
          ) : !critical.data?.length ? (
            <EmptyState message="Nenhum item abaixo do limiar." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produto</TableHead>
                  <TableHead className="text-right">Saldo</TableHead>
                  <TableHead className="text-right">Mínimo</TableHead>
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
                    <TableCell className="text-right">
                      {formatNumber(item.min_stock, 3)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DashboardPanel>

        <DashboardPanel
          title="Últimas vendas"
          description={periodHint}
          actionHref="/sales"
          actionLabel="Ver todas"
        >
          {sales.isLoading ? (
            <TableSkeleton rows={6} cols={4} />
          ) : !sales.data?.length ? (
            <EmptyState
              message="Nenhuma venda encontrada."
              actionLabel="Ver vendas"
              actionHref="/sales"
            />
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
                {sales.data.slice(0, 6).map((sale) => {
                  const status = saleStatusBadge(sale.status);
                  return (
                    <TableRow key={sale.id}>
                      <TableCell>
                        <Link
                          href={`/sales/${sale.id}`}
                          className="font-medium hover:underline"
                        >
                          {sale.id}
                        </Link>
                      </TableCell>
                      <TableCell>{formatDate(sale.sale_date)}</TableCell>
                      <TableCell>
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMoney(sale.total_amount)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </DashboardPanel>

        <DashboardPanel
          title="Últimas compras"
          actionHref="/purchases"
          actionLabel="Ver todas"
        >
          {purchases.isLoading ? (
            <TableSkeleton rows={6} cols={4} />
          ) : !purchases.data?.length ? (
            <EmptyState
              message="Nenhuma compra encontrada."
              actionLabel="Ver compras"
              actionHref="/purchases"
            />
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
                {purchases.data.map((po) => {
                  const status = purchaseStatusBadge(po.status);
                  return (
                    <TableRow key={po.id}>
                      <TableCell>
                        <Link
                          href={`/purchases/${po.id}`}
                          className="font-medium hover:underline"
                        >
                          {po.invoice_number ?? po.id}
                        </Link>
                      </TableCell>
                      <TableCell>{po.supplier_name ?? po.supplier_id}</TableCell>
                      <TableCell>
                        <Badge variant={status.variant}>{status.label}</Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMoney(po.total_amount)}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </DashboardPanel>
      </div>
    </RequirePermission>
  );
}

function MetricCard({
  label,
  value,
  hint,
  note,
  loading,
}: {
  label: string;
  value: string;
  hint?: string;
  note?: string;
  loading?: boolean;
}) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardDescription className="text-xs font-medium tracking-wide uppercase">
          {label}
        </CardDescription>
        {loading ? (
          <div className="mt-1 h-8 w-24 animate-pulse rounded-md bg-muted" />
        ) : (
          <CardTitle className="text-2xl font-semibold tracking-tight">
            {value}
          </CardTitle>
        )}
        {hint ? (
          <p className="text-xs text-muted-foreground">{hint}</p>
        ) : null}
        {note && !loading ? (
          <p className="text-xs text-muted-foreground">{note}</p>
        ) : null}
      </CardHeader>
    </Card>
  );
}

function DashboardPanel({
  title,
  description,
  actionHref,
  actionLabel,
  children,
}: {
  title: string;
  description?: string;
  actionHref: string;
  actionLabel: string;
  children: ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="border-b">
        <CardTitle>{title}</CardTitle>
        {description ? <CardDescription>{description}</CardDescription> : null}
        <CardAction>
          <Link
            href={actionHref}
            className="text-xs text-muted-foreground hover:underline"
          >
            {actionLabel}
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="pt-(--card-spacing)">{children}</CardContent>
    </Card>
  );
}

function TableSkeleton({ rows, cols }: { rows: number; cols: number }) {
  return (
    <div className="space-y-2" aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex gap-3">
          {Array.from({ length: cols }, (_, j) => (
            <div
              key={j}
              className="h-4 flex-1 animate-pulse rounded bg-muted"
              style={{ maxWidth: j === cols - 1 ? "4rem" : undefined }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
