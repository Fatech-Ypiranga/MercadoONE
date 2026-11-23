import { apiFetch } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type LoginRequest = components["schemas"]["LoginRequest"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type MeResponse = components["schemas"]["MeResponse"];
export type ChangePasswordRequest = components["schemas"]["ChangePasswordRequest"];
export type PasswordResetRequest = components["schemas"]["PasswordResetRequest"];
export type PasswordResetConfirmRequest = components["schemas"]["PasswordResetConfirmRequest"];

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

export function requestPasswordReset(body: PasswordResetRequest): Promise<unknown> {
  return apiFetch("/auth/password/request", { method: "post", body, auth: false });
}

export function checkPasswordResetToken(token: string): Promise<{ valid: boolean }> {
  return apiFetch("/auth/password/check", { method: "post", body: { token }, auth: false });
}

export function confirmPasswordReset(body: PasswordResetConfirmRequest): Promise<void> {
  return apiFetch("/auth/password/confirm", { method: "post", body, auth: false });
}
