"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

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
import { useEntityDialog } from "@/hooks/use-entity-dialog";
import {
  createCategory,
  deleteCategory,
  listCategories,
  updateCategory,
  type CategoryResponse,
} from "@/lib/api/categories-api";
import { visibleCategoryRows } from "@/lib/category-display";
import { errorMessage } from "@/lib/format";
import { slugify } from "@/lib/slugify";

const categorySchema = z.object({
  name: z.string().trim().min(1, "Informe o nome da categoria"),
  slug: z.string().trim().min(1, "Informe o slug"),
  is_active: z.boolean(),
  parent_id: z.number().nullable(),
});

type CategoryForm = z.infer<typeof categorySchema>;

const emptyForm: CategoryForm = { name: "", slug: "", is_active: true, parent_id: null };

export default function CategoriesPage() {
  const canWrite = useCan("categories", "write");
  const qc = useQueryClient();
  const dialog = useEntityDialog<CategoryResponse>();
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("all");

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<CategoryForm>({
    resolver: zodResolver(categorySchema),
    defaultValues: emptyForm,
  });
  const parentId = watch("parent_id");

  const list = useQuery({
    queryKey: ["categories", search, activeFilter],
    queryFn: () =>
      listCategories({
        q: search.trim() || undefined,
        is_active:
          activeFilter === "all" ? undefined : activeFilter === "active",
        limit: 200,
      }),
  });

  const displayRows = visibleCategoryRows(list.data ?? []);

  const save = useMutation({
    mutationFn: async (values: CategoryForm) => {
      const payload = {
        name: values.name,
        slug: values.slug || slugify(values.name),
        is_active: values.is_active,
        parent_id: values.parent_id ?? undefined,
      };
      if (dialog.editing) {
        return updateCategory(dialog.editing.id, payload);
      }
      return createCategory(payload);
    },
    onSuccess: async () => {
      dialog.close();
      reset(emptyForm);
      await qc.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteCategory(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["categories"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  function openCreate(parentIdValue: number | null = null) {
    dialog.openCreate();
    reset({ ...emptyForm, parent_id: parentIdValue });
  }

  function openEdit(item: CategoryResponse) {
    dialog.openEdit(item);
    reset({
      name: item.name,
      slug: item.slug,
      is_active: item.is_active,
      parent_id: item.parent_id ?? null,
    });
  }

  function renderRow(item: CategoryResponse, isChild = false) {
    return (
      <TableRow key={item.id}>
        <TableCell className={`font-medium${isChild ? " pl-8 text-muted-foreground" : ""}`}>
          {isChild ? "↳ " : ""}{item.name}
        </TableCell>
        <TableCell className="text-muted-foreground">{item.slug}</TableCell>
        <TableCell>
          <Badge variant={item.is_active ? "default" : "secondary"}>
            {item.is_active ? "Ativa" : "Inativa"}
          </Badge>
        </TableCell>
        {canWrite ? (
          <TableCell className="space-x-2 text-right">
            {!isChild && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => openCreate(item.id)}
                title="Adicionar subcategoria"
              >
                + Sub
              </Button>
            )}
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
    );
  }

  return (
    <RequirePermission module="categories">
      <PageHeader
        title="Categorias"
        description="Cadastro de categorias de produtos."
        actionLabel={canWrite ? "Nova categoria" : undefined}
        onAction={canWrite ? () => openCreate(null) : undefined}
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

      <ErrorAlert message={dialog.error || (list.error ? errorMessage(list.error) : null)} />

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
              {displayRows.map(({ item, isChild }) => renderRow(item, isChild))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog
        open={dialog.open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) dialog.close();
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {dialog.editing
                ? "Editar categoria"
                : parentId
                ? "Nova subcategoria"
                : "Nova categoria"}
            </DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((values) => save.mutate(values))} noValidate>
            <div className="space-y-3">
              {parentId && !dialog.editing && (
                <p className="text-sm text-muted-foreground">
                  Subcategoria de:{" "}
                  <strong>{list.data?.find((c) => c.id === parentId)?.name}</strong>
                </p>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="cat-name">Nome</Label>
                <Input
                  id="cat-name"
                  aria-invalid={Boolean(errors.name)}
                  {...register("name", {
                    onChange: (e) => {
                      if (!dialog.editing) {
                        setValue("slug", slugify(e.target.value));
                      }
                    },
                  })}
                />
                {errors.name ? (
                  <p className="text-sm text-destructive">{errors.name.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cat-slug">Slug</Label>
                <Input id="cat-slug" aria-invalid={Boolean(errors.slug)} {...register("slug")} />
                {errors.slug ? (
                  <p className="text-sm text-destructive">{errors.slug.message}</p>
                ) : null}
              </div>
              <div className="flex items-center gap-2 text-sm">
                <input id="cat-active" type="checkbox" {...register("is_active")} />
                <Label htmlFor="cat-active" className="cursor-pointer font-normal">
                  Ativa
                </Label>
              </div>
              <ErrorAlert message={dialog.error} />
            </div>
            <DialogFooter className="mt-4">
              <Button type="button" variant="outline" onClick={dialog.close}>
                Cancelar
              </Button>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Salvando…" : "Salvar"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </RequirePermission>
  );
}
