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
