export const DASHBOARD_PERIOD_DAYS = 7;
export const DASHBOARD_SALES_LIMIT = 200;

type SaleLike = {
  total_amount: string | number;
  status: string;
};

export type StatusBadge = {
  label: string;
  variant: "default" | "secondary" | "destructive" | "outline";
};

const SALE_STATUS: Record<string, StatusBadge> = {
  Concluida: { label: "Concluída", variant: "default" },
  Em_Andamento: { label: "Em andamento", variant: "secondary" },
  Suspensa: { label: "Suspensa", variant: "secondary" },
  Cancelada: { label: "Cancelada", variant: "destructive" },
};

const PURCHASE_STATUS: Record<string, StatusBadge> = {
  Confirmado: { label: "Confirmado", variant: "default" },
  Rascunho: { label: "Rascunho", variant: "secondary" },
  Cancelado: { label: "Cancelado", variant: "destructive" },
};

/** ISO date (YYYY-MM-DD) for `date_from` — start of the rolling N-day window. */
export function periodStartIso(days = DASHBOARD_PERIOD_DAYS): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  d.setDate(d.getDate() - (days - 1));
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

export function summarizeSales(sales: SaleLike[]): {
  revenue: number;
  count: number;
  capped: boolean;
} {
  let revenue = 0;
  let count = 0;
  for (const sale of sales) {
    if (sale.status === "Cancelada") continue;
    count += 1;
    revenue += Number(sale.total_amount) || 0;
  }
  return {
    revenue,
    count,
    capped: sales.length >= DASHBOARD_SALES_LIMIT,
  };
}

export function saleStatusBadge(status: string): StatusBadge {
  return SALE_STATUS[status] ?? { label: status, variant: "outline" };
}

export function purchaseStatusBadge(status: string): StatusBadge {
  return PURCHASE_STATUS[status] ?? { label: status, variant: "outline" };
}
