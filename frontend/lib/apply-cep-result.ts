export type CepAddressFields = {
  description: string;
  zip_code: string;
  street: string;
  number: string;
  complement: string;
  neighborhood: string;
  city: string;
  state: string;
  ibge_code: string;
};

export type CepLookupData = {
  street: string;
  neighborhood: string;
  city: string;
  state: string;
  ibge_code: string | null;
};

export function digitsOnly(value: string): string {
  return value.replace(/\D/g, "");
}

/**
 * Whether a CEP lookup response should be applied given the current form CEP
 * and the request generation that started the lookup.
 */
export function shouldApplyCepResult(options: {
  requestId: number;
  latestRequestId: number;
  lookedUpDigits: string;
  currentZipCode: string;
}): boolean {
  if (options.requestId !== options.latestRequestId) return false;
  return digitsOnly(options.currentZipCode) === options.lookedUpDigits;
}

/**
 * Merge a successful CEP lookup into the latest form state, preserving
 * fields the user may have edited during the async request (number,
 * complement, description, and the current zip formatting).
 */
export function mergeCepSuccess(
  current: CepAddressFields,
  data: CepLookupData,
): CepAddressFields {
  return {
    ...current,
    street: data.street,
    neighborhood: data.neighborhood,
    city: data.city,
    state: data.state,
    ibge_code: data.ibge_code ?? "",
  };
}
