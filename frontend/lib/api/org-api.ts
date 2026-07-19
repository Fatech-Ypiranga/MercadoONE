import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type UserResponse = components["schemas"]["UserResponse"];
export type UserCreate = components["schemas"]["UserCreate"];
export type UserUpdate = components["schemas"]["UserUpdate"];
export type UserPasswordReset = components["schemas"]["UserPasswordReset"];
export type UserPdvPinResponse = components["schemas"]["UserPdvPinResponse"];
export type UserProfile = components["schemas"]["UserProfile"];
export type BranchResponse = components["schemas"]["BranchResponse"];
export type StoreResponse = components["schemas"]["StoreResponse"];

export type ListUsersParams = {
  q?: string;
  profile?: UserProfile;
  is_active?: boolean;
};

export async function listUsers(params: ListUsersParams = {}): Promise<UserResponse[]> {
  return unwrapPageItems<UserResponse>(
    apiFetch("/users/", {
      method: "get",
      query: {
        limit: 200,
        q: params.q || undefined,
        profile: params.profile || undefined,
        is_active: params.is_active,
      },
    }),
  );
}

export function createUser(body: UserCreate): Promise<UserResponse> {
  return apiFetch("/users/", { method: "post", body });
}

export function updateUser(id: number, body: UserUpdate): Promise<UserResponse> {
  return apiFetch("/users/{user_id}", {
    method: "put",
    pathParams: { user_id: id },
    body,
  });
}

export function deleteUser(id: number): Promise<void> {
  return apiFetch("/users/{user_id}", {
    method: "delete",
    pathParams: { user_id: id },
  });
}

export function resetUserPassword(
  id: number,
  body: UserPasswordReset,
): Promise<UserResponse> {
  return apiFetch("/users/{user_id}/password", {
    method: "patch",
    pathParams: { user_id: id },
    body,
  });
}

export function generateUserPdvPin(id: number): Promise<UserPdvPinResponse> {
  return apiFetch("/users/{user_id}/pdv-pin", {
    method: "post",
    pathParams: { user_id: id },
  });
}

export function regenerateUserPdvId(id: number): Promise<UserResponse> {
  return apiFetch("/users/{user_id}/pdv-id/regenerate", {
    method: "post",
    pathParams: { user_id: id },
  });
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

export type CompanyResponse = components["schemas"]["CompanyResponse"];
export type CompanyUpdate = components["schemas"]["CompanyUpdate"];

export function getMyCompany(): Promise<CompanyResponse> {
  return apiFetch("/companies/me", { method: "get" });
}

export function updateMyCompany(body: CompanyUpdate): Promise<CompanyResponse> {
  return apiFetch("/companies/me", { method: "patch", body });
}
