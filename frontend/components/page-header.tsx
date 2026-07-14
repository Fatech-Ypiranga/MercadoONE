"use client";

import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";

type PageHeaderProps = {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionDisabled?: boolean;
  /** Controles extras à esquerda da ação principal (ex.: Atualizar). */
  trailing?: ReactNode;
};

export function PageHeader({
  title,
  description,
  actionLabel,
  onAction,
  actionDisabled,
  trailing,
}: PageHeaderProps) {
  const hasActions = Boolean(trailing) || Boolean(actionLabel && onAction);

  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {hasActions ? (
        <div className="flex flex-wrap items-center gap-2 sm:justify-end">
          {trailing}
          {actionLabel && onAction ? (
            <Button type="button" onClick={onAction} disabled={actionDisabled}>
              {actionLabel}
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
