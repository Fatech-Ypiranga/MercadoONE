export function formatMoney(value: string | number | null | undefined): string {
  const n = typeof value === "string" ? Number(value) : (value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export function formatNumber(
  value: string | number | null | undefined,
  digits = 0,
): string {
  const n = typeof value === "string" ? Number(value) : (value ?? 0);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("pt-BR");
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("pt-BR");
}

export function errorMessage(error: unknown, fallback = "Ocorreu um erro"): string {
  // ApiError carries a server-provided message (already user-facing, in
  // Portuguese). Any other Error — most commonly a network failure like
  // "TypeError: Failed to fetch" — is not something a user should see verbatim.
  if (error && typeof error === "object" && "name" in error && error.name === "ApiError") {
    const message = (error as { message?: string }).message;
    if (message) return message;
  }
  if (error instanceof Error && error.message) {
    return "Não foi possível conectar à API. Verifique sua conexão e tente novamente.";
  }
  return fallback;
}
