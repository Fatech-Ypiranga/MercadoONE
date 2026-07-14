"use client";

import { useAuth } from "@/components/auth-provider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function StoreSelector() {
  const { stores, activeStoreId, setStoreId, storesLoading } = useAuth();

  if (storesLoading) {
    return (
      <div className="h-8 w-40 animate-pulse rounded-lg border border-border bg-muted/40" />
    );
  }

  if (stores.length === 0) {
    return (
      <span className="text-sm text-muted-foreground">Nenhuma loja</span>
    );
  }

  const value = activeStoreId != null ? String(activeStoreId) : undefined;

  return (
    <Select
      value={value}
      onValueChange={(next) => {
        if (next != null) setStoreId(Number(next));
      }}
    >
      <SelectTrigger className="w-44 sm:w-52" size="sm" aria-label="Loja ativa">
        <SelectValue placeholder="Selecionar loja" />
      </SelectTrigger>
      <SelectContent align="end">
        {stores.map((store) => (
          <SelectItem key={store.id} value={String(store.id)}>
            {store.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
