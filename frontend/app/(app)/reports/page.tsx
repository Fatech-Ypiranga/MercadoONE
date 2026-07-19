"use client";

import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  getAverageTicket,
  getCriticalStock,
  getTopProducts,
} from "@/lib/api/reports-api";
import { errorMessage, formatMoney, formatNumber } from "@/lib/format";
import { latestDataUpdatedAt, liveQueryOptions } from "@/lib/live-query";

export default function ReportsPage() {
  const { activeStoreId, activeStore } = useAuth();
  const storeQuery = activeStoreId ?? undefined;

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

  const err = top.error || ticket.error || critical.error;
  const isFetching = top.isFetching || ticket.isFetching || critical.isFetching;
  const dataUpdatedAt = latestDataUpdatedAt(
    top.dataUpdatedAt,
    ticket.dataUpdatedAt,
    critical.dataUpdatedAt,
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
          <h2 className="mb-3 text-sm font-semibold">Top produtos</h2>
          {top.isLoading ? (
            <LoadingState />
          ) : !top.data?.length ? (
            <EmptyState message="Sem dados." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produto</TableHead>
                  <TableHead className="text-right">Qtd vendida</TableHead>
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
          <h2 className="mb-3 text-sm font-semibold">Estoque crítico</h2>
          {critical.isLoading ? (
            <LoadingState />
          ) : !critical.data?.length ? (
            <EmptyState message="Nenhum item crítico." />
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
                {critical.data.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.name}</TableCell>
                    <TableCell className="text-right">
                      {formatNumber(item.current_stock, 3)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(item.min_stock, 3)}
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
