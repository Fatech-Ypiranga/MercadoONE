import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type UserResponse = components["schemas"]["UserResponse"];
export type BranchResponse = components["schemas"]["BranchResponse"];
export type StoreResponse = components["schemas"]["StoreResponse"];

export async function listUsers(): Promise<UserResponse[]> {
  return unwrapPageItems<UserResponse>(
    apiFetch("/users/", { method: "get", query: { limit: 200 } }),
  );
}

export async function listBranches(): Promise<BranchResponse[]> {
  return unwrapPageItems<BranchResponse>(
    apiFetch("/branches/", { method: "get", query: { limit: 200 } }),
  );
}

export async function listOrgStores(): Promise<StoreResponse[]> {
  return unwrapPageItems<StoreResponse>(
    apiFetch("/stores/", { method: "get", query: { limit: 200 } }),
  );
}
