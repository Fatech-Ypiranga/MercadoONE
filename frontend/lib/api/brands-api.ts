import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type BrandResponse = components["schemas"]["BrandResponse"];
export type BrandCreate = components["schemas"]["BrandCreate"];
export type BrandUpdate = components["schemas"]["BrandUpdate"];

export async function listBrands(): Promise<BrandResponse[]> {
  return unwrapPageItems<BrandResponse>(
    apiFetch("/brands/", { method: "get", query: { limit: 200 } }),
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
