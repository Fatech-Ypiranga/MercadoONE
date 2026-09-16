import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type AuditLogResponse = components["schemas"]["AuditLogResponse"];

export function listAuditLog(): Promise<AuditLogResponse[]> {
  return unwrapPageItems<AuditLogResponse>(
    apiFetch("/audit-log/", {
      method: "get",
      query: { limit: 50, offset: 0 },
    }),
  );
}
