import { apiFetch } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type MeResponse = components["schemas"]["MeResponse"];
export type ChangePasswordRequest = components["schemas"]["ChangePasswordRequest"];

export function login(body: LoginRequest): Promise<TokenResponse> {
  return apiFetch("/auth/login", {
    method: "post",
    body,
    auth: false,
  });
}

export function fetchMe(): Promise<MeResponse> {
  return apiFetch("/auth/me", { method: "get" });
}

export function changePassword(body: ChangePasswordRequest): Promise<void> {
  return apiFetch("/auth/change-password", {
    method: "post",
    body,
  });
}
