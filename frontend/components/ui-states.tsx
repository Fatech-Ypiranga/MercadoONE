"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";

export function ErrorAlert({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <Alert variant="destructive" className="mb-4">
      <AlertDescription>{message}</AlertDescription>
    </Alert>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p className="rounded-lg border border-dashed border-border px-4 py-10 text-center text-sm text-muted-foreground">
      {message}
    </p>
  );
}

export function LoadingState({ message = "Carregando…" }: { message?: string }) {
  return <p className="text-sm text-muted-foreground">{message}</p>;
}
