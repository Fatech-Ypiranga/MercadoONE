"use client";

import { RequirePermission } from "@/components/require-permission";

type ModulePlaceholderProps = {
  title: string;
  description?: string;
  module: string;
  action?: "read" | "write" | "cancel";
};

export function ModulePlaceholder({
  title,
  description = "Tela do 1º release — em construção.",
  module,
  action = "read",
}: ModulePlaceholderProps) {
  return (
    <RequirePermission module={module} action={action}>
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </RequirePermission>
  );
}
