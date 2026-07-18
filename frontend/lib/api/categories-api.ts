import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type CategoryResponse = components["schemas"]["CategoryResponse"] & {
  parent_id?: number | null;
};
export type CategoryCreate = components["schemas"]["CategoryCreate"] & {
  parent_id?: number | null;
};
export type CategoryUpdate = components["schemas"]["CategoryUpdate"] & {
  parent_id?: number | null;
};

export type ListCategoriesQuery = {
  q?: string;
  is_active?: boolean;
  parent_id?: number;
  offset?: number;
  limit?: number;
};

export function listCategories(): Promise<CategoryResponse[]>;
export function listCategories(query: ListCategoriesQuery): Promise<CategoryResponse[]>;
export async function listCategories(
  query?: ListCategoriesQuery,
): Promise<CategoryResponse[]> {
  return unwrapPageItems<CategoryResponse>(
    apiFetch("/categories/", {
      method: "get",
      query: { ...query, limit: query?.limit ?? 200 },
    }),
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
