import { apiFetch } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type StockMovementResponse = components["schemas"]["StockMovementResponse"];
export type StockMovementCreate = components["schemas"]["StockMovementCreate"];

export type StockBalanceResponse = {
  product_id: number;
  store_id: number;
  current_balance: number | string;
};

export type StoreBalanceRow = {
  product_id: number;
  sku: string;
  name: string;
  current_balance: number | string;
};

export function getStockBalance(productId: number, storeId?: number | null) {
  return apiFetch("/stock/product/{product_id}/balance", {
    method: "get",
    pathParams: { product_id: productId },
    query: { store_id: storeId ?? undefined },
  }) as Promise<StockBalanceResponse>;
}

export function getStockExtract(productId: number, storeId?: number | null) {
  return apiFetch("/stock/product/{product_id}/extract", {
    method: "get",
    pathParams: { product_id: productId },
    query: { store_id: storeId ?? undefined },
  }) as Promise<StockMovementResponse[]>;
}

export function moveStock(body: StockMovementCreate) {
  return apiFetch("/stock/move", { method: "post", body });
}

/** Visão geral produto × saldo para uma loja (N GETs de balance — mockup). */
export async function listStoreBalances(
  storeId: number,
  products: Array<{ id: number; sku: string; name: string }>,
): Promise<StoreBalanceRow[]> {
  const rows = await Promise.all(
    products.map(async (product) => {
      const balance = await getStockBalance(product.id, storeId);
      return {
        product_id: product.id,
        sku: product.sku,
        name: product.name,
        current_balance: balance.current_balance,
      };
    }),
  );
  return rows;
}
