"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  createBrand,
  deleteBrand,
  listBrands,
  updateBrand,
  type BrandResponse,
} from "@/lib/api/brands-api";
import { errorMessage } from "@/lib/format";

export default function BrandsPage() {
  const canWrite = useCan("brands", "write");
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<BrandResponse | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const list = useQuery({
    queryKey: ["brands", search],
    queryFn: () => listBrands({ q: search.trim() || undefined }),
  });

  const save = useMutation({
    mutationFn: async () => {
      const payload = { name: name.trim() };
      if (editing) return updateBrand(editing.id, payload);
      return createBrand(payload);
    },
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setName("");
      setError(null);
      await qc.invalidateQueries({ queryKey: ["brands"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteBrand(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["brands"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  return (
    <RequirePermission module="brands">
      <PageHeader
        title="Marcas"
        description="Cadastro de marcas de produtos."
        actionLabel={canWrite ? "Nova marca" : undefined}
        onAction={
          canWrite
            ? () => {
                setEditing(null);
                setName("");
                setError(null);
                setOpen(true);
              }
            : undefined
        }
      />

      <div className="mb-4">
        <Input
          placeholder="Buscar por nome…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
      </div>

      <ErrorAlert message={error || (list.error ? errorMessage(list.error) : null)} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhuma marca cadastrada." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  {canWrite ? (
                    <TableCell className="space-x-2 text-right">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditing(item);
                          setName(item.name);
                          setError(null);
                          setOpen(true);
                        }}
                      >
                        Editar
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Excluir marca "${item.name}"?`)) {
                            remove.mutate(item.id);
                          }
                        }}
                      >
                        Excluir
                      </Button>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar marca" : "Nova marca"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="brand-name">Nome</Label>
              <Input
                id="brand-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <ErrorAlert message={error} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={!name.trim() || save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </RequirePermission>
  );
}
