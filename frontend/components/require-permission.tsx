"use client";

import Link from "next/link";

import { useAuth } from "@/components/auth-provider";
import { can, type UserProfile } from "@/lib/permissions";

type RequirePermissionProps = {
  module: string;
  action?: "read" | "write" | "cancel";
  children: React.ReactNode;
};

export function ForbiddenState({
  title = "Acesso negado",
  description = "Seu perfil não tem permissão para esta área.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
      <p className="text-sm font-medium text-destructive">403</p>
      <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      <p className="text-sm text-muted-foreground">{description}</p>
      <Link
        href="/dashboard"
        className="inline-flex h-8 items-center rounded-lg border border-border px-3 text-sm font-medium hover:bg-muted"
      >
        Voltar ao dashboard
      </Link>
    </div>
  );
}

export function RequirePermission({
  module,
  action = "read",
  children,
}: RequirePermissionProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <p className="text-sm text-muted-foreground">Verificando permissão…</p>
    );
  }

  if (!user) return null;

  if (!can(user.profile as UserProfile, module, action)) {
    return <ForbiddenState />;
  }

  return <>{children}</>;
}
