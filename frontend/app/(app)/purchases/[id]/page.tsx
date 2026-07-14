"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useParams } from "next/navigation";

import { PageHeader } from "@/components/page-header";
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
import { getPurchase } from "@/lib/api/purchases-api";
import { errorMessage, formatDateTime, formatMoney, formatNumber } from "@/lib/format";

export default function PurchaseDetailPage() {
  const params = useParams<{ id: string }>();
  const purchaseId = Number(params.id);

  const detail = useQuery({
    queryKey: ["purchases", purchaseId],
    queryFn: () => getPurchase(purchaseId),
    enabled: Number.isFinite(purchaseId),
  });

  return (
    <RequirePermission module="purchases">
      <PageHeader
        title={
          detail.data
            ? `Compra NF ${detail.data.invoice_number ?? detail.data.id}`
            : "Detalhe da compra"
        }
        description="Itens e totais da entrada de mercadoria."
      />

      <div className="mb-4">
        <Link
          href="/purchases"
          className="inline-flex h-8 items-center rounded-lg border border-border px-3 text-sm hover:bg-muted"
        >
          Voltar
        </Link>
      </div>

      <ErrorAlert message={detail.error ? errorMessage(detail.error) : null} />

      {detail.isLoading ? (
        <LoadingState />
      ) : !detail.data ? (
        <EmptyState message="Compra não encontrada." />
      ) : (
        <div className="space-y-6">
          <dl className="grid gap-4 rounded-xl border border-border p-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Fornecedor</dt>
              <dd className="mt-1 text-sm font-medium">
                {detail.data.supplier_name ?? detail.data.supplier_id}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Status</dt>
              <dd className="mt-1">
                <Badge>{detail.data.status}</Badge>
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Entrada</dt>
              <dd className="mt-1 text-sm">
                {formatDateTime(detail.data.entry_date)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground uppercase">Total</dt>
              <dd className="mt-1 text-sm font-semibold">
                {formatMoney(detail.data.total_amount)}
              </dd>
            </div>
          </dl>

          <div className="rounded-xl border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Produto</TableHead>
                  <TableHead>Cód. forn.</TableHead>
                  <TableHead className="text-right">Qtd</TableHead>
                  <TableHead className="text-right">Custo un.</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detail.data.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>
                      {item.product_name ?? `#${item.product_id}`}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {item.supplier_product_code ?? "—"}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatNumber(item.quantity, 3)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatMoney(item.unit_cost)}
                    </TableCell>
                    <TableCell className="text-right">
                      {formatMoney(item.total_cost)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </RequirePermission>
  );
}
