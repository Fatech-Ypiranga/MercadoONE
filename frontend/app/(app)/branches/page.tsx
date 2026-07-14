"use client";

import { useQuery } from "@tanstack/react-query";

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
import { listBranches } from "@/lib/api/org-api";
import { errorMessage } from "@/lib/format";

export default function BranchesPage() {
  const list = useQuery({ queryKey: ["branches"], queryFn: listBranches });

  return (
    <RequirePermission module="branches" action="write">
      <PageHeader
        title="Filiais"
        description="Filiais da empresa (Admin/Gerente)."
      />

      <ErrorAlert message={list.error ? errorMessage(list.error) : null} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhuma filial." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Nome</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((branch) => (
                <TableRow key={branch.id}>
                  <TableCell className="font-mono text-xs">{branch.code}</TableCell>
                  <TableCell className="font-medium">{branch.name}</TableCell>
                  <TableCell>
                    <Badge variant={branch.is_active ? "default" : "secondary"}>
                      {branch.is_active ? "Ativa" : "Inativa"}
                    </Badge>
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
