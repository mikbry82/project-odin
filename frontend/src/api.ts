import type {
  AIAnalysis,
  Analysis,
  AutoCycle,
  AutoSettings,
  MarketResponse,
  Performance,
  Portfolio,
  ScannerResponse,
  Strategy,
  StrategyEvaluation,
  SystemStatus,
  TradingMode,
} from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const DEFAULT_ERROR = "Begäran misslyckades";
const REQUEST_TIMEOUT_MS = 10_000;

type ErrorPayload = { detail?: string };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Odin Core svarade inte i tid. Försök igen.");
    }
    throw new Error("Kunde inte ansluta till Odin Core.");
  } finally {
    window.clearTimeout(timeout);
  }

  const contentType = response.headers.get("content-type") ?? "";
  let body: T | ErrorPayload | string;
  try {
    body = contentType.includes("application/json")
      ? ((await response.json()) as T | ErrorPayload)
      : await response.text();
  } catch {
    throw new Error("Odin Core skickade ett ogiltigt svar. Försök igen.");
  }

  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : undefined;
    throw new Error(typeof detail === "string" ? detail : DEFAULT_ERROR);
  }

  if (!contentType.includes("application/json")) {
    throw new Error("Odin Core skickade ett oväntat svar. Försök igen.");
  }

  return body as T;
}

const jsonBody = (value: unknown): Pick<RequestInit, "body"> => ({
  body: JSON.stringify(value),
});

export const api = {
  getStatus: () => request<SystemStatus>("/api/v1/system/status"),
  setMode: (tradingMode: TradingMode) =>
    request<SystemStatus>("/api/v1/system/mode", {
      method: "PUT",
      ...jsonBody({ trading_mode: tradingMode }),
    }),
  getMarkets: () => request<MarketResponse>("/api/v1/markets"),
  getAnalysis: (symbol: string, interval: string) =>
    request<Analysis>(
      `/api/v1/markets/${symbol}/analysis?interval=${interval}&limit=240`,
    ),
  getPortfolio: () => request<Portfolio>("/api/v1/paper/portfolio"),
  placeOrder: (
    symbol: string,
    side: "buy" | "sell",
    amountUsdt: number,
    stopLossPercent: number,
    takeProfitPercent: number,
  ) =>
    request<Portfolio>("/api/v1/paper/orders", {
      method: "POST",
      ...jsonBody({
        symbol,
        side,
        amount_usdt: amountUsdt,
        stop_loss_percent: stopLossPercent,
        take_profit_percent: takeProfitPercent,
      }),
    }),
  getScanner: (interval: string) =>
    request<ScannerResponse>(`/api/v1/scanner?interval=${interval}`),
  getAutoSettings: () => request<AutoSettings>("/api/v1/scanner/auto/settings"),
  saveAutoSettings: (settings: AutoSettings) =>
    request<AutoSettings>("/api/v1/scanner/auto/settings", {
      method: "PUT",
      ...jsonBody(settings),
    }),
  runAutoCycle: () =>
    request<AutoCycle>("/api/v1/scanner/auto/run", { method: "POST" }),
  getPerformance: () => request<Performance>("/api/v1/scanner/performance"),
  getAIAnalysis: (symbol: string, interval: string) =>
    request<AIAnalysis>(
      `/api/v1/ai/analysis?symbol=${symbol}&interval=${interval}`,
    ),
  getStrategies: () => request<Strategy[]>("/api/v1/strategies"),
  saveStrategy: (strategy: Strategy) =>
    request<Strategy>(`/api/v1/strategies/${strategy.id}`, {
      method: "PUT",
      ...jsonBody({
        name: strategy.name,
        description: strategy.description,
        enabled: strategy.enabled,
        parameters: strategy.parameters,
        risk_profile: strategy.risk_profile,
      }),
    }),
  activateStrategy: (id: number) =>
    request<Strategy>(`/api/v1/strategies/${id}/activate`, {
      method: "POST",
    }),
  duplicateStrategy: (id: number) =>
    request<Strategy>(`/api/v1/strategies/${id}/duplicate`, {
      method: "POST",
    }),
  evaluateStrategy: (id: number, symbol: string, interval: string) =>
    request<StrategyEvaluation>(
      `/api/v1/strategies/${id}/evaluate?symbol=${symbol}&interval=${interval}`,
    ),
};
