import { apiFetch, unwrapPageItems } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type CustomerResponse = components["schemas"]["CustomerResponse"];
export type CustomerDetailResponse = components["schemas"]["CustomerDetailResponse"];
export type CustomerCreate = components["schemas"]["CustomerCreate"];
export type CustomerUpdate = components["schemas"]["CustomerUpdate"];
export type CustomerAddressCreate = components["schemas"]["CustomerAddressCreate"];
export type CustomerAddressUpdate = components["schemas"]["CustomerAddressUpdate"];
export type CustomerAddressResponse = components["schemas"]["CustomerAddressResponse"];

export async function listCustomers(): Promise<CustomerResponse[]> {
  return unwrapPageItems<CustomerResponse>(
    apiFetch("/customers/", { method: "get", query: { limit: 200 } }),
  );
}

export function getCustomer(customerId: number) {
  return apiFetch("/customers/{customer_id}", {
    method: "get",
    pathParams: { customer_id: customerId },
  });
}

export function createCustomer(body: CustomerCreate) {
  return apiFetch("/customers/", { method: "post", body });
}

export function updateCustomer(customerId: number, body: CustomerUpdate) {
  return apiFetch("/customers/{customer_id}", {
    method: "put",
    pathParams: { customer_id: customerId },
    body,
  });
}

export function deleteCustomer(customerId: number) {
  return apiFetch("/customers/{customer_id}", {
    method: "delete",
    pathParams: { customer_id: customerId },
  });
}

export function createCustomerAddress(
  customerId: number,
  body: CustomerAddressCreate,
) {
  return apiFetch("/customers/{customer_id}/addresses", {
    method: "post",
    pathParams: { customer_id: customerId },
    body,
  });
}

export function updateCustomerAddress(
  customerId: number,
  addressId: number,
  body: CustomerAddressUpdate,
) {
  return apiFetch("/customers/{customer_id}/addresses/{address_id}", {
    method: "put",
    pathParams: { customer_id: customerId, address_id: addressId },
    body,
  });
}

export function deleteCustomerAddress(customerId: number, addressId: number) {
  return apiFetch("/customers/{customer_id}/addresses/{address_id}", {
    method: "delete",
    pathParams: { customer_id: customerId, address_id: addressId },
  });
}
