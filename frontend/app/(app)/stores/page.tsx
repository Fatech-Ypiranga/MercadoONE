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
import { listOrgStores } from "@/lib/api/org-api";
import { errorMessage } from "@/lib/format";

export default function StoresPage() {
  const list = useQuery({ queryKey: ["stores"], queryFn: listOrgStores });

  return (
    <RequirePermission module="stores" action="write">
      <PageHeader
        title="Lojas"
        description="Lojas da empresa (Admin/Gerente). A loja ativa (estoque/compras/vendas) fica no header."
      />

      <ErrorAlert message={list.error ? errorMessage(list.error) : null} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhuma loja." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Código</TableHead>
                <TableHead>Nome</TableHead>
                <TableHead>Filial</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((store) => (
                <TableRow key={store.id}>
                  <TableCell className="font-mono text-xs">{store.code}</TableCell>
                  <TableCell className="font-medium">{store.name}</TableCell>
                  <TableCell>#{store.branch_id}</TableCell>
                  <TableCell>
                    <Badge variant={store.is_active ? "default" : "secondary"}>
                      {store.is_active ? "Ativa" : "Inativa"}
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
