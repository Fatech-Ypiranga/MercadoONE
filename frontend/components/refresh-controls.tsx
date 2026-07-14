"use client";

import { Button } from "@/components/ui/button";

type RefreshControlsProps = {
  dataUpdatedAt?: number;
  isFetching?: boolean;
  onRefresh: () => void;
};

function formatUpdatedAt(ts: number): string {
  return new Date(ts).toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function RefreshControls({
  dataUpdatedAt,
  isFetching,
  onRefresh,
}: RefreshControlsProps) {
  return (
    <div className="flex flex-wrap items-center gap-2 sm:gap-3">
      <span className="text-xs text-muted-foreground">
        {dataUpdatedAt
          ? `Última atualização: ${formatUpdatedAt(dataUpdatedAt)}`
          : "Ainda não atualizado"}
      </span>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={onRefresh}
        disabled={isFetching}
      >
        {isFetching ? "Atualizando…" : "Atualizar"}
      </Button>
    </div>
  );
}
