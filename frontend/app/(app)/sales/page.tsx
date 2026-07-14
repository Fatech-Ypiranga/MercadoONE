"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page-header";
import { RefreshControls } from "@/components/refresh-controls";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
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
import { listSales } from "@/lib/api/sales-api";
import { errorMessage, formatDate, formatMoney } from "@/lib/format";
import { liveQueryOptions } from "@/lib/live-query";

export default function SalesPage() {
  const { activeStoreId, activeStore, stores } = useAuth();
  const [status, setStatus] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const storeNameById = useMemo(() => {
    const map = new Map<number, string>();
    for (const store of stores) map.set(store.id, store.name);
    return map;
  }, [stores]);

  const list = useQuery({
    queryKey: ["sales", activeStoreId, status, dateFrom, dateTo],
    queryFn: () =>
      listSales({
        store_id: activeStoreId ?? undefined,
        status: status || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      }),
    ...liveQueryOptions,
  });

  return (
    <RequirePermission module="sales">
      <PageHeader
        title="Vendas"
        description={
          activeStore
            ? `Vendas da loja ${activeStore.name}. Caixa/PDV fica no app externo.`
            : "Listagem e detalhe de vendas (mockup de API)."
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

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Status</Label>
          <select
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="">Todos os status</option>
            <option value="Em_Andamento">Em andamento</option>
            <option value="Concluida">Concluída</option>
            <option value="Cancelada">Cancelada</option>
            <option value="Suspensa">Suspensa</option>
          </select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">De</Label>
          <Input
            type="date"
            className="h-8 w-auto"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Até</Label>
          <Input
            type="date"
            className="h-8 w-auto"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
      </div>

      <ErrorAlert message={list.error ? errorMessage(list.error) : null} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhuma venda encontrada." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Data</TableHead>
                <TableHead>Loja</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Itens</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((sale) => (
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
                    {storeNameById.get(sale.store_id) ?? `#${sale.store_id}`}
                  </TableCell>
                  <TableCell>{sale.status}</TableCell>
                  <TableCell>{sale.items?.length ?? 0}</TableCell>
                  <TableCell className="text-right">
                    {formatMoney(sale.total_amount)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </RequirePermission>
  );
}
