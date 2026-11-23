import { apiFetch } from "@/lib/api/client";

export type TopProductItem = {
  id: number;
  name: string;
  total_sold: number | string;
};

export type AverageTicketResponse = {
  average_ticket: number | string;
};

export type CriticalStockItem = {
  id: number;
  name: string;
  current_stock: number | string;
  min_stock: number | string;
};

export type SalesGroupRow = {
  id: number;
  name: string;
  sales_count: number;
  total_amount: number | string;
  average_ticket: number | string;
};

export type SalesGroupQuery = {
  store_id?: number;
  date_from?: string;
  date_to?: string;
  limit?: number;
};

export function getSalesByOperator(query?: SalesGroupQuery) {
  return apiFetch("/reports/sales-by-operator", {
    method: "get",
    query,
  }) as Promise<SalesGroupRow[]>;
}

export function getSalesByCustomer(query?: SalesGroupQuery) {
  return apiFetch("/reports/sales-by-customer", {
    method: "get",
    query,
  }) as Promise<SalesGroupRow[]>;
}

export function getTopProducts(query?: { limit?: number; store_id?: number }) {
  return apiFetch("/reports/top-products", {
    method: "get",
    query,
  }) as Promise<TopProductItem[]>;
}

export function getAverageTicket(query?: { store_id?: number }) {
  return apiFetch("/reports/average-ticket", {
    method: "get",
    query,
  }) as Promise<AverageTicketResponse>;
}

export function getCriticalStock(query?: {
  min_threshold?: number;
  store_id?: number;
}) {
  return apiFetch("/reports/critical-stock", {
    method: "get",
    query,
  }) as Promise<CriticalStockItem[]>;
}
