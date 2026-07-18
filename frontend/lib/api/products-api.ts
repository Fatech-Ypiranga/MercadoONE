import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type ProductResponse = components["schemas"]["ProductResponse"];
export type ProductDetailResponse = components["schemas"]["ProductDetailResponse"];
export type ProductCreate = components["schemas"]["ProductCreate"];
export type ProductUpdate = components["schemas"]["ProductUpdate"];

export type ListProductsQuery = {
  q?: string;
  offset?: number;
  limit?: number;
  category_id?: number;
  material_code?: string;
  primary_supplier_id?: number;
  is_active?: boolean;
};

export function listProducts(): Promise<ProductResponse[]>;
export function listProducts(query: ListProductsQuery): Promise<ProductResponse[]>;
export async function listProducts(query?: ListProductsQuery): Promise<ProductResponse[]> {
  return unwrapPageItems<ProductResponse>(
    apiFetch("/products/", {
      method: "get",
      query: { ...query, limit: query?.limit ?? 50 },
    }),
  );
}

export function getProduct(productId: number) {
  return apiFetch("/products/{product_id}", {
    method: "get",
    pathParams: { product_id: productId },
  });
}

export function createProduct(body: ProductCreate) {
  return apiFetch("/products/", { method: "post", body });
}

export function updateProduct(productId: number, body: ProductUpdate) {
  return apiFetch("/products/{product_id}", {
    method: "put",
    pathParams: { product_id: productId },
    body,
  });
}

export function deleteProduct(productId: number) {
  return apiFetch("/products/{product_id}", {
    method: "delete",
    pathParams: { product_id: productId },
  });
}
