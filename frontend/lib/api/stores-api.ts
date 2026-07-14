import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type StoreResponse = components["schemas"]["StoreResponse"];

export async function listStores(): Promise<StoreResponse[]> {
  return unwrapPageItems<StoreResponse>(
    apiFetch("/stores/", { method: "get", query: { limit: 200 } }),
  );
}
