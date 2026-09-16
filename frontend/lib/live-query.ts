/** Polling do mockup para espelhar dados gravados por Data Sim / PDV. */
const LIVE_REFETCH_INTERVAL_MS = 20_000;

/** Opções TanStack Query para listagens/consultas “ao vivo”. */
export const liveQueryOptions = {
  refetchInterval: LIVE_REFETCH_INTERVAL_MS,
  staleTime: 0,
} as const;

/** Prefixo de queryKeys invalidados ao trocar a loja ativa. */
export const STORE_SCOPED_QUERY_ROOTS = [
  "sales",
  "purchases",
  "stock",
  "reports",
] as const;

export function latestDataUpdatedAt(
  ...timestamps: Array<number | undefined>
): number | undefined {
  const values = timestamps.filter(
    (value): value is number => typeof value === "number" && value > 0,
  );
  return values.length ? Math.max(...values) : undefined;
}
