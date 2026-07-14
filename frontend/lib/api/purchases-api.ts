import { apiFetch, apiUpload, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type PurchaseOrderResponse = components["schemas"]["PurchaseOrderResponse"];
export type PurchaseOrderDetailResponse =
  components["schemas"]["PurchaseOrderDetailResponse"];
export type NfeUploadPreviewResponse =
  components["schemas"]["NfeUploadPreviewResponse"];
export type PurchaseConfirmRequest = components["schemas"]["PurchaseConfirmRequest"];

export async function listPurchases(query?: {
  supplier_id?: number;
  status?: string;
  date_from?: string;
  date_to?: string;
  store_id?: number;
  limit?: number;
  offset?: number;
}): Promise<PurchaseOrderResponse[]> {
  return unwrapPageItems<PurchaseOrderResponse>(
    apiFetch("/purchases/", {
      method: "get",
      query: { ...query, limit: query?.limit ?? 200 },
    }),
  );
}

export function getPurchase(purchaseId: number) {
  return apiFetch("/purchases/{purchase_id}", {
    method: "get",
    pathParams: { purchase_id: purchaseId },
  });
}

export function uploadPurchaseXml(file: File) {
  return apiUpload<NfeUploadPreviewResponse>("/purchases/upload-xml", file);
}

export function confirmPurchase(body: PurchaseConfirmRequest) {
  return apiFetch("/purchases/confirm", { method: "post", body });
}

export function cancelPurchase(purchaseId: number) {
  return apiFetch("/purchases/{purchase_id}/cancel", {
    method: "post",
    pathParams: { purchase_id: purchaseId },
  });
}
