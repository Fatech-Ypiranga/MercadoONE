import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type CategoryResponse = components["schemas"]["CategoryResponse"];
export type CategoryCreate = components["schemas"]["CategoryCreate"];
export type CategoryUpdate = components["schemas"]["CategoryUpdate"];

export async function listCategories(): Promise<CategoryResponse[]> {
  return unwrapPageItems<CategoryResponse>(
    apiFetch("/categories/", { method: "get", query: { limit: 200 } }),
  );
}

export function createCategory(body: CategoryCreate) {
  return apiFetch("/categories/", { method: "post", body });
}

export function updateCategory(categoryId: number, body: CategoryUpdate) {
  return apiFetch("/categories/{category_id}", {
    method: "put",
    pathParams: { category_id: categoryId },
    body,
  });
}

export function deleteCategory(categoryId: number) {
  return apiFetch("/categories/{category_id}", {
    method: "delete",
    pathParams: { category_id: categoryId },
  });
}
