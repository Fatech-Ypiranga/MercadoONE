"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { RequirePermission } from "@/components/require-permission";
import { EmptyState, ErrorAlert, LoadingState } from "@/components/ui-states";
import { Badge } from "@/components/ui/badge";
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
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
  type CategoryResponse,
} from "@/lib/api/categories-api";
import { errorMessage } from "@/lib/format";
import { slugify } from "@/lib/slugify";

type FormState = { name: string; slug: string; is_active: boolean };

const emptyForm: FormState = { name: "", slug: "", is_active: true };

export default function CategoriesPage() {
  const canWrite = useCan("categories", "write");
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<CategoryResponse | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("all");

  const list = useQuery({
    queryKey: ["categories", search, activeFilter],
    queryFn: () =>
      listCategories({
        q: search.trim() || undefined,
        is_active:
          activeFilter === "all" ? undefined : activeFilter === "active",
      }),
  });

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        name: form.name.trim(),
        slug: form.slug.trim() || slugify(form.name),
        is_active: form.is_active,
      };
      if (editing) {
        return updateCategory(editing.id, payload);
      }
      return createCategory(payload);
    },
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError(null);
    setOpen(true);
  }

  function openEdit(item: CategoryResponse) {
    setEditing(item);
    setForm({
      name: item.name,
      slug: item.slug,
      is_active: item.is_active,
    });
    setError(null);
    setOpen(true);
  }

  return (
    <RequirePermission module="categories">
      <PageHeader
        title="Categorias"
        description="Cadastro de categorias de produtos."
        actionLabel={canWrite ? "Nova categoria" : undefined}
        onAction={canWrite ? openCreate : undefined}
      />

      <div className="mb-4 flex flex-wrap gap-2">
        <Input
          placeholder="Buscar por nome ou slug…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
        <select
          className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm"
          value={activeFilter}
          onChange={(e) =>
            setActiveFilter(e.target.value as typeof activeFilter)
          }
        >
          <option value="all">Todas</option>
          <option value="active">Ativas</option>
          <option value="inactive">Inativas</option>
        </select>
      </div>

      <ErrorAlert message={error || (list.error ? errorMessage(list.error) : null)} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhuma categoria cadastrada." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Status</TableHead>
                {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.name}</TableCell>
                  <TableCell className="text-muted-foreground">{item.slug}</TableCell>
                  <TableCell>
                    <Badge variant={item.is_active ? "default" : "secondary"}>
                      {item.is_active ? "Ativa" : "Inativa"}
                    </Badge>
                  </TableCell>
                  {canWrite ? (
                    <TableCell className="space-x-2 text-right">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => openEdit(item)}
                      >
                        Editar
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Excluir categoria "${item.name}"?`)) {
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
            <DialogTitle>
              {editing ? "Editar categoria" : "Nova categoria"}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="cat-name">Nome</Label>
              <Input
                id="cat-name"
                value={form.name}
                onChange={(e) => {
                  const name = e.target.value;
                  setForm((prev) => ({
                    ...prev,
                    name,
                    slug: editing ? prev.slug : slugify(name),
                  }));
                }}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="cat-slug">Slug</Label>
              <Input
                id="cat-slug"
                value={form.slug}
                onChange={(e) => setForm((prev) => ({ ...prev, slug: e.target.value }))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, is_active: e.target.checked }))
                }
              />
              Ativa
            </label>
            <ErrorAlert message={error} />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={!form.name.trim() || save.isPending}
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
