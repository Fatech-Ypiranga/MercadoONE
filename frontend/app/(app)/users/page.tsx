"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Pencil, RefreshCw, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { useAuth } from "@/components/auth-provider";
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
  Sheet,
  SheetContent,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
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
import { listBranches } from "@/lib/api/org-api";
import { listStores } from "@/lib/api/stores-api";
import {
  createUser,
  deleteUser,
  generateUserPdvPin,
  listUsers,
  regenerateUserPdvId,
  resetUserPassword,
  updateUser,
  type UserProfile,
  type UserResponse,
} from "@/lib/api/users-api";
import { errorMessage } from "@/lib/format";

const PROFILES: UserProfile[] = [
  "admin",
  "gerente",
  "supervisor",
  "operador",
  "conferente",
  "colaborador",
];

const SUPERVISOR_PLUS = new Set<UserProfile>(["admin", "gerente", "supervisor"]);
const PDV_ELIGIBLE = new Set<UserProfile>([
  "admin",
  "gerente",
  "supervisor",
  "operador",
]);

const userSchema = z
  .object({
    full_name: z.string().trim().min(1, "Informe o nome completo"),
    cpf: z.string(),
    email: z.string(),
    username: z.string(),
    password: z.string(),
    profile: z.enum(PROFILES as [UserProfile, ...UserProfile[]]),
    is_active: z.boolean(),
    default_branch_id: z.string(),
    default_store_id: z.string(),
    is_editing: z.boolean(),
  })
  .superRefine((data, ctx) => {
    if (data.cpf.replace(/\D/g, "").length !== 11) {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["cpf"], message: "CPF deve ter 11 dígitos" });
    }
    if (!data.email.trim() && !data.username.trim()) {
      const message = "Informe e-mail ou usuário";
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["email"], message });
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["username"], message });
    }
    if (!data.is_editing && data.password.length < 6) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["password"],
        message: "Senha deve ter ao menos 6 caracteres",
      });
    }
  });

type UserForm = z.infer<typeof userSchema>;

const emptyForm: UserForm = {
  full_name: "",
  cpf: "",
  email: "",
  username: "",
  password: "",
  profile: "operador",
  is_active: true,
  default_branch_id: "",
  default_store_id: "",
  is_editing: false,
};

export default function UsersPage() {
  const canWrite = useCan("users", "write");
  const { user: currentUser } = useAuth();
  const hasBranches = Boolean(currentUser?.company?.has_branches);
  const qc = useQueryClient();
  const dialog = useEntityDialog<UserResponse>();
  const [search, setSearch] = useState("");
  const [profileFilter, setProfileFilter] = useState<string>("");
  const [activeFilter, setActiveFilter] = useState<string>("");
  const [passwordUser, setPasswordUser] = useState<UserResponse | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [pinReveal, setPinReveal] = useState<{
    user: UserResponse;
    pin: string;
    pdvId: string;
  } | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<UserForm>({
    resolver: zodResolver(userSchema),
    defaultValues: emptyForm,
  });
  const defaultBranchId = watch("default_branch_id");

  const list = useQuery({
    queryKey: ["users", search, profileFilter, activeFilter],
    queryFn: () =>
      listUsers({
        q: search.trim() || undefined,
        profile: (profileFilter || undefined) as UserProfile | undefined,
        is_active:
          activeFilter === ""
            ? undefined
            : activeFilter === "true"
              ? true
              : false,
      }),
  });

  const branches = useQuery({
    queryKey: ["branches"],
    queryFn: listBranches,
    enabled: canWrite && hasBranches,
  });
  const stores = useQuery({
    queryKey: ["stores"],
    queryFn: listStores,
    enabled: canWrite,
  });

  const filteredStores = useMemo(() => {
    if (!hasBranches) return stores.data ?? [];
    const branchId = defaultBranchId ? Number(defaultBranchId) : null;
    if (!branchId || !stores.data) return stores.data ?? [];
    return stores.data.filter((store) => store.branch_id === branchId);
  }, [defaultBranchId, hasBranches, stores.data]);

  const save = useMutation({
    mutationFn: async (values: UserForm) => {
      const payload = {
        full_name: values.full_name.trim(),
        cpf: values.cpf.replace(/\D/g, ""),
        email: values.email.trim() || null,
        username: values.username.trim() || null,
        profile: values.profile,
        is_active: values.is_active,
        default_branch_id: values.default_branch_id
          ? Number(values.default_branch_id)
          : null,
        default_store_id: values.default_store_id
          ? Number(values.default_store_id)
          : null,
      };
      if (dialog.editing) return updateUser(dialog.editing.id, payload);
      return createUser({ ...payload, password: values.password });
    },
    onSuccess: async () => {
      dialog.close();
      reset(emptyForm);
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const resetPassword = useMutation({
    mutationFn: async () => {
      if (!passwordUser) throw new Error("Usuário não selecionado");
      return resetUserPassword(passwordUser.id, { new_password: newPassword });
    },
    onSuccess: () => {
      setPasswordUser(null);
      setNewPassword("");
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const generatePin = useMutation({
    mutationFn: (user: UserResponse) => generateUserPdvPin(user.id),
    onSuccess: async (data, user) => {
      setPinReveal({ user, pin: data.pdv_pin, pdvId: data.pdv_id });
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  const regeneratePdv = useMutation({
    mutationFn: (id: number) => regenerateUserPdvId(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => dialog.setError(errorMessage(err)),
  });

  function openCreate() {
    dialog.openCreate();
    reset(emptyForm);
  }

  function openEdit(user: UserResponse) {
    dialog.openEdit(user);
    reset({
      full_name: user.full_name,
      cpf: user.cpf,
      email: user.email || "",
      username: user.username || "",
      password: "",
      profile: user.profile,
      is_active: user.is_active,
      default_branch_id: user.default_branch_id ? String(user.default_branch_id) : "",
      default_store_id: user.default_store_id ? String(user.default_store_id) : "",
      is_editing: true,
    });
  }

  return (
    <RequirePermission module="users">
      <PageHeader
        title="Usuários"
        description="Cadastro de usuários da empresa (somente Admin)."
        actionLabel={canWrite ? "Novo usuário" : undefined}
        onAction={canWrite ? openCreate : undefined}
      />

      <div className="mb-4 flex flex-wrap gap-3">
        <Input
          placeholder="Buscar nome, login, CPF ou PDV ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-md"
        />
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={profileFilter}
          onChange={(e) => setProfileFilter(e.target.value)}
        >
          <option value="">Todos os perfis</option>
          {PROFILES.map((profile) => (
            <option key={profile} value={profile}>
              {profile}
            </option>
          ))}
        </select>
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
        >
          <option value="">Ativos e inativos</option>
          <option value="true">Somente ativos</option>
          <option value="false">Somente inativos</option>
        </select>
      </div>

      <ErrorAlert message={dialog.error || (list.error ? errorMessage(list.error) : null)} />

      {list.isLoading ? (
        <LoadingState />
      ) : !list.data?.length ? (
        <EmptyState message="Nenhum usuário encontrado." />
      ) : (
        <div className="rounded-xl border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Login</TableHead>
                <TableHead>Perfil</TableHead>
                <TableHead>PDV ID</TableHead>
                <TableHead>PIN PDV</TableHead>
                <TableHead>Status</TableHead>
                {canWrite ? <TableHead className="text-right">Ações</TableHead> : null}
              </TableRow>
            </TableHeader>
            <TableBody>
              {list.data.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.full_name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {user.email || user.username || "—"}
                  </TableCell>
                  <TableCell>{user.profile}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {user.pdv_id || "—"}
                  </TableCell>
                  <TableCell>
                    {SUPERVISOR_PLUS.has(user.profile) ? (
                      <Badge variant={user.has_pdv_pin ? "default" : "secondary"}>
                        {user.has_pdv_pin ? "Definido" : "Ausente"}
                      </Badge>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.is_active ? "default" : "secondary"}>
                      {user.is_active ? "Ativo" : "Inativo"}
                    </Badge>
                  </TableCell>
                  {canWrite ? (
                    <TableCell className="text-right">
                      <div className="flex justify-end items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                        {SUPERVISOR_PLUS.has(user.profile) ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => generatePin.mutate(user)}
                          >
                            PIN PDV
                          </Button>
                        ) : null}
                        {PDV_ELIGIBLE.has(user.profile) ? (
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon-sm"
                            title="Gerar novo ID de PDV"
                            aria-label="Gerar novo ID de PDV"
                            onClick={() => {
                              if (
                                confirm(
                                  "Regenerar o ID de PDV? O código anterior deixará de funcionar.",
                                )
                              ) {
                                regeneratePdv.mutate(user.id);
                              }
                            }}
                          >
                            <RefreshCw className="size-3.5" />
                          </Button>
                        ) : null}
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          title="Redefinir senha"
                          aria-label="Redefinir senha"
                          onClick={() => {
                            setPasswordUser(user);
                            setNewPassword("");
                          }}
                        >
                          <KeyRound className="size-3.5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => openEdit(user)}
                          aria-label="Editar usuário"
                        >
                          <Pencil className="size-3.5" />
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                          onClick={() => {
                            if (confirm(`Excluir ${user.full_name}?`)) {
                              remove.mutate(user.id);
                            }
                          }}
                          aria-label="Excluir usuário"
                        >
                          <Trash2 className="size-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  ) : null}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Sheet
        open={dialog.open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) dialog.close();
        }}
      >
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>{dialog.editing ? "Editar usuário" : "Novo usuário"}</SheetTitle>
          </SheetHeader>
          <form
            onSubmit={handleSubmit((values) => save.mutate(values))}
            noValidate
            className="flex flex-1 flex-col overflow-y-auto px-4"
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5 sm:col-span-2">
                <Label htmlFor="usr-name">Nome completo</Label>
                <Input
                  id="usr-name"
                  aria-invalid={Boolean(errors.full_name)}
                  {...register("full_name")}
                />
                {errors.full_name ? (
                  <p className="text-sm text-destructive">{errors.full_name.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="usr-cpf">CPF</Label>
                <Input id="usr-cpf" aria-invalid={Boolean(errors.cpf)} {...register("cpf")} />
                {errors.cpf ? (
                  <p className="text-sm text-destructive">{errors.cpf.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="usr-profile">Perfil</Label>
                <select
                  id="usr-profile"
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  {...register("profile")}
                >
                  {PROFILES.map((profile) => (
                    <option key={profile} value={profile}>
                      {profile}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="usr-email">E-mail</Label>
                <Input
                  id="usr-email"
                  aria-invalid={Boolean(errors.email)}
                  {...register("email")}
                />
                {errors.email ? (
                  <p className="text-sm text-destructive">{errors.email.message}</p>
                ) : null}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="usr-username">Usuário</Label>
                <Input
                  id="usr-username"
                  aria-invalid={Boolean(errors.username)}
                  {...register("username")}
                />
                {errors.username ? (
                  <p className="text-sm text-destructive">{errors.username.message}</p>
                ) : null}
              </div>
              {!dialog.editing ? (
                <div className="space-y-1.5 sm:col-span-2">
                  <Label htmlFor="usr-password">Senha de login</Label>
                  <Input
                    id="usr-password"
                    type="password"
                    aria-invalid={Boolean(errors.password)}
                    {...register("password")}
                  />
                  {errors.password ? (
                    <p className="text-sm text-destructive">{errors.password.message}</p>
                  ) : null}
                </div>
              ) : null}
              {hasBranches ? (
                <div className="space-y-1.5">
                  <Label htmlFor="usr-branch">Filial padrão</Label>
                  <select
                    id="usr-branch"
                    className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                    {...register("default_branch_id")}
                  >
                    <option value="">Nenhuma</option>
                    {(branches.data ?? []).map((branch) => (
                      <option key={branch.id} value={branch.id}>
                        {branch.code} — {branch.name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
              <div className="space-y-1.5">
                <Label htmlFor="usr-store">Loja padrão</Label>
                <select
                  id="usr-store"
                  className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                  {...register("default_store_id")}
                >
                  <option value="">Nenhuma</option>
                  {filteredStores.map((store) => (
                    <option key={store.id} value={store.id}>
                      {store.code} — {store.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2 text-sm sm:col-span-2">
                <input id="usr-active" type="checkbox" {...register("is_active")} />
                <Label htmlFor="usr-active" className="cursor-pointer font-normal">
                  Ativo
                </Label>
              </div>
              {dialog.editing?.pdv_id ? (
                <p className="text-sm text-muted-foreground sm:col-span-2">
                  PDV ID atual: <span className="font-mono">{dialog.editing.pdv_id}</span>
                </p>
              ) : null}
            </div>
            <ErrorAlert message={dialog.error} />
            <SheetFooter className="flex-row justify-end gap-2 border-t border-border px-0">
              <Button type="button" variant="outline" onClick={dialog.close}>
                Cancelar
              </Button>
              <Button type="submit" disabled={save.isPending}>
                {save.isPending ? "Salvando…" : "Salvar"}
              </Button>
            </SheetFooter>
          </form>
        </SheetContent>
      </Sheet>

      <Dialog
        open={passwordUser != null}
        onOpenChange={(next) => {
          if (!next) setPasswordUser(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Redefinir senha — {passwordUser?.full_name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label>Nova senha de login</Label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setPasswordUser(null)}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={resetPassword.isPending || newPassword.length < 6}
              onClick={() => resetPassword.mutate()}
            >
              Redefinir
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={pinReveal != null}
        onOpenChange={(next) => {
          if (!next) setPinReveal(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>PIN PDV gerado</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 text-sm">
            <p>
              Guarde agora — o PIN não será exibido novamente. Pode ser digitado ou
              impresso como código de barras.
            </p>
            <p>
              Usuário: <strong>{pinReveal?.user.full_name}</strong>
            </p>
            <p>
              PDV ID:{" "}
              <span className="font-mono text-base">{pinReveal?.pdvId}</span>
            </p>
            <p>
              PIN:{" "}
              <span className="font-mono text-lg tracking-wider">{pinReveal?.pin}</span>
            </p>
          </div>
          <DialogFooter>
            <Button type="button" onClick={() => setPinReveal(null)}>
              Entendi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </RequirePermission>
  );
}
