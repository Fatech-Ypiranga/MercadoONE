"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";

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
  createUser,
  deleteUser,
  generateUserPdvPin,
  listBranches,
  listOrgStores,
  listUsers,
  regenerateUserPdvId,
  resetUserPassword,
  updateUser,
  type UserProfile,
  type UserResponse,
} from "@/lib/api/org-api";
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

type FormState = {
  full_name: string;
  cpf: string;
  email: string;
  username: string;
  password: string;
  profile: UserProfile;
  is_active: boolean;
  default_branch_id: string;
  default_store_id: string;
};

const emptyForm: FormState = {
  full_name: "",
  cpf: "",
  email: "",
  username: "",
  password: "",
  profile: "operador",
  is_active: true,
  default_branch_id: "",
  default_store_id: "",
};

export default function UsersPage() {
  const canWrite = useCan("users", "write");
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<UserResponse | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState<string | null>(null);
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
    enabled: canWrite,
  });
  const stores = useQuery({
    queryKey: ["stores"],
    queryFn: listOrgStores,
    enabled: canWrite,
  });

  const filteredStores = useMemo(() => {
    const branchId = form.default_branch_id
      ? Number(form.default_branch_id)
      : null;
    if (!branchId || !stores.data) return stores.data ?? [];
    return stores.data.filter((store) => store.branch_id === branchId);
  }, [form.default_branch_id, stores.data]);

  const save = useMutation({
    mutationFn: async () => {
      const payload = {
        full_name: form.full_name.trim(),
        cpf: form.cpf.replace(/\D/g, ""),
        email: form.email.trim() || null,
        username: form.username.trim() || null,
        profile: form.profile,
        is_active: form.is_active,
        default_branch_id: form.default_branch_id
          ? Number(form.default_branch_id)
          : null,
        default_store_id: form.default_store_id
          ? Number(form.default_store_id)
          : null,
      };
      if (editing) return updateUser(editing.id, payload);
      return createUser({ ...payload, password: form.password });
    },
    onSuccess: async () => {
      setOpen(false);
      setEditing(null);
      setForm(emptyForm);
      setError(null);
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const resetPassword = useMutation({
    mutationFn: async () => {
      if (!passwordUser) throw new Error("Usuário não selecionado");
      return resetUserPassword(passwordUser.id, { new_password: newPassword });
    },
    onSuccess: () => {
      setPasswordUser(null);
      setNewPassword("");
      setError(null);
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const generatePin = useMutation({
    mutationFn: (user: UserResponse) => generateUserPdvPin(user.id),
    onSuccess: async (data, user) => {
      setPinReveal({ user, pin: data.pdv_pin, pdvId: data.pdv_id });
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  const regeneratePdv = useMutation({
    mutationFn: (id: number) => regenerateUserPdvId(id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(errorMessage(err)),
  });

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError(null);
    setOpen(true);
  }

  function openEdit(user: UserResponse) {
    setEditing(user);
    setForm({
      full_name: user.full_name,
      cpf: user.cpf,
      email: user.email || "",
      username: user.username || "",
      password: "",
      profile: user.profile,
      is_active: user.is_active,
      default_branch_id: user.default_branch_id
        ? String(user.default_branch_id)
        : "",
      default_store_id: user.default_store_id
        ? String(user.default_store_id)
        : "",
    });
    setError(null);
    setOpen(true);
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

      <ErrorAlert message={error || (list.error ? errorMessage(list.error) : null)} />

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
                    <TableCell className="space-x-2 text-right">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => openEdit(user)}
                      >
                        Editar
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setPasswordUser(user);
                          setNewPassword("");
                          setError(null);
                        }}
                      >
                        Senha
                      </Button>
                      {SUPERVISOR_PLUS.has(user.profile) ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() => generatePin.mutate(user)}
                        >
                          PIN PDV
                        </Button>
                      ) : null}
                      {PDV_ELIGIBLE.has(user.profile) ? (
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
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
                          Novo PDV ID
                        </Button>
                      ) : null}
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          if (confirm(`Excluir ${user.full_name}?`)) {
                            remove.mutate(user.id);
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
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? "Editar usuário" : "Novo usuário"}</DialogTitle>
          </DialogHeader>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Nome completo</Label>
              <Input
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>CPF</Label>
              <Input
                value={form.cpf}
                onChange={(e) => setForm({ ...form, cpf: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Perfil</Label>
              <select
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={form.profile}
                onChange={(e) =>
                  setForm({ ...form, profile: e.target.value as UserProfile })
                }
              >
                {PROFILES.map((profile) => (
                  <option key={profile} value={profile}>
                    {profile}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>E-mail</Label>
              <Input
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Usuário</Label>
              <Input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
              />
            </div>
            {!editing ? (
              <div className="space-y-1.5 sm:col-span-2">
                <Label>Senha de login</Label>
                <Input
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm({ ...form, password: e.target.value })}
                />
              </div>
            ) : null}
            <div className="space-y-1.5">
              <Label>Filial padrão</Label>
              <select
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={form.default_branch_id}
                onChange={(e) =>
                  setForm({
                    ...form,
                    default_branch_id: e.target.value,
                    default_store_id: "",
                  })
                }
              >
                <option value="">Nenhuma</option>
                {(branches.data ?? []).map((branch) => (
                  <option key={branch.id} value={branch.id}>
                    {branch.code} — {branch.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1.5">
              <Label>Loja padrão</Label>
              <select
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={form.default_store_id}
                onChange={(e) =>
                  setForm({ ...form, default_store_id: e.target.value })
                }
              >
                <option value="">Nenhuma</option>
                {filteredStores.map((store) => (
                  <option key={store.id} value={store.id}>
                    {store.code} — {store.name}
                  </option>
                ))}
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm sm:col-span-2">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              />
              Ativo
            </label>
            {editing?.pdv_id ? (
              <p className="text-sm text-muted-foreground sm:col-span-2">
                PDV ID atual: <span className="font-mono">{editing.pdv_id}</span>
              </p>
            ) : null}
          </div>
          <ErrorAlert message={error} />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button
              type="button"
              disabled={
                save.isPending ||
                !form.full_name.trim() ||
                form.cpf.replace(/\D/g, "").length !== 11 ||
                (!editing && form.password.length < 6) ||
                (!form.email.trim() && !form.username.trim())
              }
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Salvando…" : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
