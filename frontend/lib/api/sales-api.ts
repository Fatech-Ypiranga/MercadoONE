import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SaleDetailResponse = components["schemas"]["SaleDetailResponse"];

export async function listSales(query?: {
  customer_id?: number;
  status?: string;
  date_from?: string;
  date_to?: string;
  store_id?: number;
  limit?: number;
  offset?: number;
}): Promise<SaleDetailResponse[]> {
  return unwrapPageItems<SaleDetailResponse>(
    apiFetch("/sales/", {
      method: "get",
      query: { ...query, limit: query?.limit ?? 200 },
    }),
  );
}

export function getSale(saleId: number) {
  return apiFetch("/sales/{sale_id}", {
    method: "get",
    pathParams: { sale_id: saleId },
  });
}

export function cancelSale(saleId: number) {
  return apiFetch("/sales/{sale_id}/cancel", {
    method: "post",
    pathParams: { sale_id: saleId },
  });
}
