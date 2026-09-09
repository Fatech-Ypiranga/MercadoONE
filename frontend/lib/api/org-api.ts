import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type BranchResponse = components["schemas"]["BranchResponse"];

export async function listBranches(): Promise<BranchResponse[]> {
  return unwrapPageItems<BranchResponse>(
    apiFetch("/branches/", { method: "get", query: { limit: 200 } }),
  );
}

export type CompanyResponse = components["schemas"]["CompanyResponse"];
export type CompanyUpdate = components["schemas"]["CompanyUpdate"];

export function getMyCompany(): Promise<CompanyResponse> {
  return apiFetch("/companies/me", { method: "get" });
}

export function updateMyCompany(body: CompanyUpdate): Promise<CompanyResponse> {
  return apiFetch("/companies/me", { method: "patch", body });
}
