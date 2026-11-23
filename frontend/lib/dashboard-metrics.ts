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

export type DailyRevenuePoint = { date: string; label: string; revenue: number; count: number };

function localDateKey(d: Date): string {
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

/**
 * Receita e quantidade de vendas por dia nos últimos `days` dias (inclui hoje).
 * Dias sem venda aparecem com zero; vendas canceladas são ignoradas.
 */
export function salesByDay(
  sales: Array<SaleLike & { sale_date?: string }>,
  days = DASHBOARD_PERIOD_DAYS,
  today: Date = new Date(),
): DailyRevenuePoint[] {
  const points: DailyRevenuePoint[] = [];
  const index = new Map<string, DailyRevenuePoint>();
  for (let i = days - 1; i >= 0; i -= 1) {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i);
    const key = localDateKey(d);
    const point = {
      date: key,
      label: `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`,
      revenue: 0,
      count: 0,
    };
    points.push(point);
    index.set(key, point);
  }
  for (const sale of sales) {
    if (sale.status === "Cancelada" || !sale.sale_date) continue;
    const when = new Date(sale.sale_date);
    if (Number.isNaN(when.getTime())) continue;
    const point = index.get(localDateKey(when));
    if (!point) continue;
    point.revenue += Number(sale.total_amount) || 0;
    point.count += 1;
  }
  return points;
}

export type PaymentSlice = { method: string; label: string; revenue: number; count: number };

const PAYMENT_LABEL: Record<string, string> = {
  dinheiro: "Dinheiro",
  cartao: "Cartão",
  cartao_credito: "Cartão de crédito",
  cartao_debito: "Cartão de débito",
  credito: "Crédito",
  debito: "Débito",
  pix: "PIX",
  fiado: "Fiado",
};

/**
 * Receita por forma de pagamento, da maior para a menor. Soma por pagamento (vendas
 * com pagamento dividido contam em cada forma); vendas sem `payments` usam
 * `payment_method` com o total; sem forma informada vira "Não informado".
 */
export function salesByPaymentMethod(
  sales: Array<
    SaleLike & {
      payment_method?: string | null;
      payments?: Array<{ method: string; amount: string | number }> | null;
    }
  >,
): PaymentSlice[] {
  const map = new Map<string, PaymentSlice>();
  const add = (rawMethod: string | null | undefined, amount: number) => {
    const raw = (rawMethod ?? "").trim().toLowerCase();
    const method = raw || "nao_informado";
    const label =
      PAYMENT_LABEL[method] ?? (raw ? raw.charAt(0).toUpperCase() + raw.slice(1) : "Não informado");
    const slice = map.get(method) ?? { method, label, revenue: 0, count: 0 };
    slice.revenue += amount;
    slice.count += 1;
    map.set(method, slice);
  };
  for (const sale of sales) {
    if (sale.status === "Cancelada") continue;
    if (sale.payments && sale.payments.length > 0) {
      for (const payment of sale.payments) add(payment.method, Number(payment.amount) || 0);
    } else {
      add(sale.payment_method, Number(sale.total_amount) || 0);
    }
  }
  return [...map.values()].sort((a, b) => b.revenue - a.revenue);
}
