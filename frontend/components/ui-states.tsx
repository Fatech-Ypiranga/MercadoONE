"use client";

import Link from "next/link";

import { Alert, AlertDescription } from "@/components/ui/alert";

export function ErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <Alert variant="destructive" className="mb-4">
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

export function EmptyState({
  message,
  actionLabel,
  actionHref,
}: {
  message: string;
  actionLabel?: string;
  actionHref?: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-border px-4 py-10 text-center">
      <p className="text-sm text-muted-foreground">{message}</p>
      {actionLabel && actionHref ? (
        <Link
          href={actionHref}
          className="mt-3 inline-block text-sm font-medium text-foreground underline-offset-4 hover:underline"
        >
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}

export function LoadingState({ message = "Carregando…" }: { message?: string }) {
  return (
    <p role="status" className="text-sm text-muted-foreground">
      {message}
    </p>
  );
}
