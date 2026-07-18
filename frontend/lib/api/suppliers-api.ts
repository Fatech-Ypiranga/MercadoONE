import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type SupplierResponse = components["schemas"]["SupplierResponse"];
export type SupplierCreate = components["schemas"]["SupplierCreate"];
export type SupplierUpdate = components["schemas"]["SupplierUpdate"];

export type ListSuppliersQuery = {
  name?: string;
  document?: string;
  code?: string;
  active_only?: boolean;
  limit?: number;
  offset?: number;
};

export function listSuppliers(): Promise<SupplierResponse[]>;
export function listSuppliers(query: ListSuppliersQuery): Promise<SupplierResponse[]>;
export async function listSuppliers(
  query?: ListSuppliersQuery,
): Promise<SupplierResponse[]> {
  return unwrapPageItems<SupplierResponse>(
    apiFetch("/suppliers/", {
      method: "get",
      query: { ...query, limit: query?.limit ?? 200 },
    }),
  );
}

export function createSupplier(body: SupplierCreate) {
  return apiFetch("/suppliers/", { method: "post", body });
}

export function updateSupplier(supplierId: number, body: SupplierUpdate) {
  return apiFetch("/suppliers/{supplier_id}", {
    method: "put",
    pathParams: { supplier_id: supplierId },
    body,
  });
}

export function deleteSupplier(supplierId: number) {
  return apiFetch("/suppliers/{supplier_id}", {
    method: "delete",
    pathParams: { supplier_id: supplierId },
  });
}
