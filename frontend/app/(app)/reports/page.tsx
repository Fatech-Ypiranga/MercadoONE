"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
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
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import {
  getAverageTicket,
  getCriticalStock,
  getSalesByCustomer,
  getSalesByOperator,
  getTopProducts,
  type SalesGroupRow,
} from "@/lib/api/reports-api";
import { errorMessage, formatMoney, formatNumber } from "@/lib/format";
import { latestDataUpdatedAt, liveQueryOptions } from "@/lib/live-query";

const CHART_TOOLTIP_STYLE = {
  background: "var(--color-card)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-md)",
  fontSize: 12.5,
  boxShadow: "0 8px 20px -6px oklch(0.2 0.02 260 / 20%)",
};
const CHART_TICK_STYLE = { fill: "var(--color-muted-foreground)", fontSize: 12 };

function SalesGroupTable({
  title,
  nameLabel,
  rows,
  loading,
  emptyMessage,
}: {
  title: string;
  nameLabel: string;
  rows: SalesGroupRow[] | undefined;
  loading: boolean;
  emptyMessage: string;
}) {
  return (
    <section className="rounded-xl border border-border p-4">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {loading ? (
        <LoadingState />
      ) : !rows?.length ? (
        <EmptyState message={emptyMessage} />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{nameLabel}</TableHead>
              <TableHead className="text-right">Vendas</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right">Ticket médio</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.name}</TableCell>
                <TableCell className="text-right">{row.sales_count}</TableCell>
                <TableCell className="text-right">{formatMoney(row.total_amount)}</TableCell>
                <TableCell className="text-right">{formatMoney(row.average_ticket)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}

export default function ReportsPage() {
  const { activeStoreId, activeStore } = useAuth();
  const storeQuery = activeStoreId ?? undefined;
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const periodQuery = {
    store_id: storeQuery,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };

  const top = useQuery({
    queryKey: ["reports", "top", storeQuery, 20],
    queryFn: () => getTopProducts({ limit: 20, store_id: storeQuery }),
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

  const byOperator = useQuery({
    queryKey: ["reports", "by-operator", storeQuery, dateFrom, dateTo],
    queryFn: () => getSalesByOperator(periodQuery),
    ...liveQueryOptions,
  });
  const byCustomer = useQuery({
    queryKey: ["reports", "by-customer", storeQuery, dateFrom, dateTo],
    queryFn: () => getSalesByCustomer(periodQuery),
    ...liveQueryOptions,
  });

  const err =
    top.error || ticket.error || critical.error || byOperator.error || byCustomer.error;
  const isFetching =
    top.isFetching ||
    ticket.isFetching ||
    critical.isFetching ||
    byOperator.isFetching ||
    byCustomer.isFetching;
  const dataUpdatedAt = latestDataUpdatedAt(
    top.dataUpdatedAt,
    ticket.dataUpdatedAt,
    critical.dataUpdatedAt,
    byOperator.dataUpdatedAt,
    byCustomer.dataUpdatedAt,
  );

  return (
    <RequirePermission module="reports">
      <PageHeader
        title="Relatórios"
        description={
          activeStore
            ? `Indicadores filtrados pela loja ${activeStore.name}.`
            : "Indicadores da empresa (sem filtro de loja)."
        }
        trailing={
          <RefreshControls
            dataUpdatedAt={dataUpdatedAt}
            isFetching={isFetching}
            onRefresh={() => {
              void top.refetch();
              void ticket.refetch();
              void critical.refetch();
              void byOperator.refetch();
              void byCustomer.refetch();
            }}
          />
        }
      />

      <ErrorAlert message={err ? errorMessage(err) : null} />

      <div className="mb-6 rounded-xl border border-border p-4">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          Ticket médio
        </p>
        <p className="mt-2 text-3xl font-semibold tracking-tight">
          {ticket.isLoading ? "…" : formatMoney(ticket.data?.average_ticket)}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-xl border border-border p-4">
          <h2 className="mb-1 text-sm font-semibold">Top produtos</h2>
          <p className="mb-3 text-xs text-muted-foreground">Unidades vendidas no período</p>
          {top.isLoading ? (
            <LoadingState />
          ) : !top.data?.length ? (
            <EmptyState message="Sem dados." />
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(200, top.data.length * 32)}>
              <BarChart
                data={top.data.map((item) => ({ ...item, total_sold: Number(item.total_sold) }))}
                layout="vertical"
                margin={{ left: 8, right: 24, top: 4, bottom: 4 }}
                barCategoryGap={6}
              >
                <CartesianGrid horizontal={false} stroke="var(--color-border)" />
                <XAxis type="number" tick={CHART_TICK_STYLE} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={CHART_TICK_STYLE}
                  axisLine={false}
                  tickLine={false}
                  width={120}
                  tickFormatter={(value: string) =>
                    value.length > 18 ? `${value.slice(0, 17)}…` : value
                  }
                />
                <Tooltip
                  cursor={{ fill: "var(--color-muted)" }}
                  contentStyle={CHART_TOOLTIP_STYLE}
                  formatter={(value) => [formatNumber(Number(value), 3), "Vendido"]}
                />
                <Bar dataKey="total_sold" fill="var(--color-primary)" radius={[0, 4, 4, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>

        <section className="rounded-xl border border-border p-4">
          <h2 className="mb-1 text-sm font-semibold">Estoque crítico</h2>
          <p className="mb-3 text-xs text-muted-foreground">Saldo atual vs. mínimo configurado</p>
          {critical.isLoading ? (
            <LoadingState />
          ) : !critical.data?.length ? (
            <EmptyState message="Nenhum item crítico." />
          ) : (
            <ResponsiveContainer width="100%" height={Math.max(200, critical.data.length * 40)}>
              <BarChart
                data={critical.data.map((item) => ({
                  ...item,
                  current_stock: Number(item.current_stock),
                  min_stock: Number(item.min_stock),
                }))}
                layout="vertical"
                margin={{ left: 8, right: 24, top: 4, bottom: 4 }}
                barCategoryGap={10}
                barGap={2}
              >
                <CartesianGrid horizontal={false} stroke="var(--color-border)" />
                <XAxis type="number" tick={CHART_TICK_STYLE} axisLine={false} tickLine={false} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={CHART_TICK_STYLE}
                  axisLine={false}
                  tickLine={false}
                  width={120}
                  tickFormatter={(value: string) =>
                    value.length > 18 ? `${value.slice(0, 17)}…` : value
                  }
                />
                <Tooltip
                  cursor={{ fill: "var(--color-muted)" }}
                  contentStyle={CHART_TOOLTIP_STYLE}
                  formatter={(value) => formatNumber(Number(value), 3)}
                />
                <Legend
                  wrapperStyle={{ fontSize: 12, color: "var(--color-muted-foreground)" }}
                  formatter={(value: string) =>
                    value === "current_stock" ? "Saldo atual" : "Mínimo"
                  }
                />
                <Bar
                  dataKey="current_stock"
                  fill="var(--color-destructive)"
                  radius={[0, 4, 4, 0]}
                  maxBarSize={12}
                />
                <Bar dataKey="min_stock" fill="var(--color-border)" radius={[0, 4, 4, 0]} maxBarSize={12} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </section>
      </div>

      <div className="mt-8 mb-3 flex flex-wrap items-end gap-4">
        <h2 className="mr-auto text-base font-semibold">Vendas por operador e por cliente</h2>
        <div className="space-y-1">
          <Label htmlFor="report_from">De</Label>
          <Input
            id="report_from"
            type="date"
            value={dateFrom}
            max={dateTo || undefined}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="report_to">Até</Label>
          <Input
            id="report_to"
            type="date"
            value={dateTo}
            min={dateFrom || undefined}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <SalesGroupTable
          title="Por operador"
          nameLabel="Operador"
          rows={byOperator.data}
          loading={byOperator.isLoading}
          emptyMessage="Sem vendas no período."
        />
        <SalesGroupTable
          title="Por cliente"
          nameLabel="Cliente"
          rows={byCustomer.data}
          loading={byCustomer.isLoading}
          emptyMessage="Nenhuma venda com cliente identificado no período."
        />
      </div>
    </RequirePermission>
  );
}
