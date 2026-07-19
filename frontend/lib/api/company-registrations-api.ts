import { apiFetch } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type CompanyRegistrationCreate =
  components["schemas"]["CompanyRegistrationCreate"];
export type CompanyRegistrationResponse =
  components["schemas"]["CompanyRegistrationResponse"];

export function createCompanyRegistration(
  body: CompanyRegistrationCreate,
): Promise<CompanyRegistrationResponse> {
  return apiFetch("/company-registrations/", {
    method: "post",
    body,
    auth: false,
  });
}
