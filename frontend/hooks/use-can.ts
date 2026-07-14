"use client";

import { can } from "@/lib/permissions";
import { useAuth } from "@/components/auth-provider";

export function useCan(module: string, action: "read" | "write" | "cancel" = "read") {
  const { user } = useAuth();
  if (!user) return false;
  return can(user.profile, module, action);
}
