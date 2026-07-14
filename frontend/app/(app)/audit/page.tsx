"use client";

import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "@/components/page-header";
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
import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import { errorMessage, formatDateTime } from "@/lib/format";
import type { components } from "@/lib/api/schema";

type AuditLogResponse = components["schemas"]["AuditLogResponse"];

function listAuditLog() {
  return unwrapPageItems<AuditLogResponse>(
    apiFetch("/audit-log/", {
      method: "get",
      query: { limit: 50, offset: 0 },
    }),
  );
}

export default function AuditPage() {
  const list = useQuery({ queryKey: ["audit-log"], queryFn: listAuditLog });

  return (
    <RequirePermission module="audit">
      <PageHeader
        title="Auditoria"
        description="Últimos registros de auditoria (Admin)."
      />

      <ErrorAlert message={list.error ? errorMessage(list.error) : null} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Sem registros." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quando</TableHead>
                <TableHead>Ação</TableHead>
                <TableHead>Entidade</TableHead>
                <TableHead>Usuário</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((row) => (
                <TableRow key={row.id}>
                  <TableCell>{formatDateTime(row.created_at)}</TableCell>
                  <TableCell>{row.action}</TableCell>
                  <TableCell>
                    {row.entity_type} #{row.entity_id}
                  </TableCell>
                  <TableCell>{row.user_id ?? "sistema"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </RequirePermission>
  );
}
