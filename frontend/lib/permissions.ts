import type { components } from "@/lib/api/schema";

export type UserProfile = components["schemas"]["UserProfile"];

type Action = "read" | "write" | "cancel" | "discount";

const ALL_READ: Partial<Record<UserProfile, Set<Action>>> = {
  admin: new Set(["read", "write"]),
  gerente: new Set(["read", "write"]),
  supervisor: new Set(["read"]),
  operador: new Set(["read"]),
  conferente: new Set(["read"]),
  colaborador: new Set(["read"]),
};

const MODULE_PERMISSIONS: Record<string, Partial<Record<UserProfile, Set<Action>>>> = {
  categories: { ...ALL_READ },
  products: { ...ALL_READ },
  customers: {
    admin: new Set(["read", "write"]),
    gerente: new Set(["read", "write"]),
    supervisor: new Set(["read"]),
    operador: new Set(["read", "write"]),
    conferente: new Set(["read"]),
    colaborador: new Set(["read"]),
  },
  sales: {
    admin: new Set(["read", "write", "cancel", "discount"]),
    gerente: new Set(["read", "write", "cancel", "discount"]),
    supervisor: new Set(["read", "write", "cancel", "discount"]),
    operador: new Set(["read", "write"]),
    conferente: new Set(["read"]),
    colaborador: new Set(["read"]),
  },
  stock: {
    admin: new Set(["read", "write"]),
    gerente: new Set(["read", "write"]),
    supervisor: new Set(["read", "write"]),
    operador: new Set(["read"]),
    conferente: new Set(["read", "write"]),
    colaborador: new Set(["read"]),
  },
  reports: {
    admin: new Set(["read"]),
    gerente: new Set(["read"]),
    supervisor: new Set(["read"]),
    operador: new Set(["read"]),
    conferente: new Set(["read"]),
    colaborador: new Set(["read"]),
  },
  users: {
    admin: new Set(["read", "write"]),
  },
  audit: {
    admin: new Set(["read"]),
  },
  suppliers: { ...ALL_READ },
  purchases: {
    admin: new Set(["read", "write"]),
    gerente: new Set(["read", "write"]),
    supervisor: new Set(["read"]),
    operador: new Set(["read"]),
    conferente: new Set(["read", "write"]),
    colaborador: new Set(["read"]),
  },
  branches: { ...ALL_READ },
  stores: { ...ALL_READ },
  companies: {
    admin: new Set(["read"]),
    gerente: new Set(["read"]),
    supervisor: new Set(["read"]),
    operador: new Set(["read"]),
    conferente: new Set(["read"]),
    colaborador: new Set(["read"]),
  },
};

export function can(
  profile: UserProfile,
  module: string,
  action: Action = "read",
): boolean {
  return MODULE_PERMISSIONS[module]?.[profile]?.has(action) ?? false;
}

export function canManageUsers(profile: UserProfile): boolean {
  return can(profile, "users", "write");
}
