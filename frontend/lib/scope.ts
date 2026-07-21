import type { components } from "@/lib/api/schema";

export type MeUser = components["schemas"]["MeResponse"];
export type StoreInfo = components["schemas"]["MeStoreInfo"];
export type CompanyInfo = components["schemas"]["MeCompanyInfo"];

const STORE_KEY = "pyerp_active_store_id";

export function getActiveStoreId(): number | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(STORE_KEY);
  if (!raw) return null;
  const id = Number(raw);
  return Number.isFinite(id) ? id : null;
}

export function setActiveStoreId(storeId: number): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORE_KEY, String(storeId));
}

export function clearActiveStoreId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORE_KEY);
}

/** Resolve loja ativa: preferência salva, senão default do usuário. */
export function resolveActiveStoreId(user: MeUser): number | null {
  const saved = getActiveStoreId();
  if (saved != null) return saved;
  return user.default_store_id ?? user.default_store?.id ?? null;
}
