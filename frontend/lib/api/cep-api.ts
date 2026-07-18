import { API_BASE_URL } from "@/lib/api/client";
import { getToken } from "@/lib/auth";

export interface CepResponse {
  zip_code: string;
  street: string;
  neighborhood: string;
  city: string;
  state: string;
  ibge_code: string | null;
}

export type CepLookupResult =
  | { status: "success"; data: CepResponse }
  | { status: "not_found"; message: string }
  | { status: "error"; message: string }
  | { status: "aborted" };

export async function lookupCep(
  cep: string,
  signal?: AbortSignal,
): Promise<CepLookupResult> {
  const digits = cep.replace(/\D/g, "");
  if (digits.length !== 8) {
    return { status: "not_found", message: "CEP inválido." };
  }

  const token = getToken();
  const headers: HeadersInit = { Accept: "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/cep/${digits}`, {
      headers,
      signal,
    });

    if (response.status === 404 || response.status === 422) {
      const body = await response.json().catch(() => ({}));
      const msg =
        typeof body?.detail === "string" ? body.detail : "CEP não encontrado.";
      return { status: "not_found", message: msg };
    }

    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const msg =
        typeof body?.detail === "string"
          ? body.detail
          : "Não foi possível consultar o CEP.";
      return { status: "error", message: msg };
    }

    const data: CepResponse = await response.json();
    return { status: "success", data };
  } catch (error) {
    if (
      signal?.aborted ||
      (error instanceof DOMException && error.name === "AbortError") ||
      (error instanceof Error && error.name === "AbortError")
    ) {
      return { status: "aborted" };
    }
    return {
      status: "error",
      message: "Não foi possível consultar o CEP. Preencha manualmente.",
    };
  }
}
