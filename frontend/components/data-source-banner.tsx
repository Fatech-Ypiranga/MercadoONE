"use client";

import { Alert, AlertDescription } from "@/components/ui/alert";

export function DataSourceBanner() {
  return (
    <Alert className="mb-6 border-border bg-muted/40">
      <AlertDescription>
        Dados de catálogo e compras vêm do ERP (CRUD neste mockup ou Data Sim);
        vendas vêm do PDV.
      </AlertDescription>
    </Alert>
  );
}
