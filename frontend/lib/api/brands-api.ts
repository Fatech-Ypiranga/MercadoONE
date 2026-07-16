import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type BrandResponse = components["schemas"]["BrandResponse"];
export type BrandCreate = components["schemas"]["BrandCreate"];
export type BrandUpdate = components["schemas"]["BrandUpdate"];

export type ListBrandsQuery = {
  q?: string;
  offset?: number;
  limit?: number;
};

export function listBrands(): Promise<BrandResponse[]>;
export function listBrands(query: ListBrandsQuery): Promise<BrandResponse[]>;
export async function listBrands(query?: ListBrandsQuery): Promise<BrandResponse[]> {
  return unwrapPageItems<BrandResponse>(
    apiFetch("/brands/", {
      method: "get",
      query: { ...query, limit: query?.limit ?? 200 },
    }),
  );
}

export function createBrand(body: BrandCreate) {
  return apiFetch("/brands/", { method: "post", body });
}

export function updateBrand(brandId: number, body: BrandUpdate) {
  return apiFetch("/brands/{brand_id}", {
    method: "put",
    pathParams: { brand_id: brandId },
    body,
  });
}

export function deleteBrand(brandId: number) {
  return apiFetch("/brands/{brand_id}", {
    method: "delete",
    pathParams: { brand_id: brandId },
  });
}
