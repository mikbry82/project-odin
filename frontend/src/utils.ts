export function formatNumber(
  value: number | null | undefined,
  digits = 2,
): string {
  if (value == null) return "—";
  return new Intl.NumberFormat("sv-SE", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function getErrorMessage(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function getSignalClass(signal?: string): "buy" | "sell" | "wait" {
  if (signal?.includes("KÖP")) return "buy";
  if (signal?.includes("SÄLJ")) return "sell";
  return "wait";
}
