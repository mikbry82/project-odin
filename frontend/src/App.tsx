import { useEffect, useMemo, useState } from "react";

import { api } from "./api";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  ErrorState,
  INTERVALS,
  IntervalSelector,
  LoadingState,
  PriceChart,
} from "./components/ui";
import type {
  AIAnalysis,
  Analysis,
  AutoCycle,
  AutoSettings,
  ExchangeConnection,
  LiveOrderPreview,
  LiveAccount,
  LiveRiskSettings,
  Market,
  Performance,
  Portfolio,
  TradingPair,
  ScannerItem,
  Strategy,
  StrategyEvaluation,
  SystemStatus,
  TradingMode,
  View,
} from "./types";
import { formatNumber as fmt, getErrorMessage, getSignalClass } from "./utils";
import { removeLegacyInterfacePreferences } from "./legacyPreferences";

const intervals = INTERVALS;
const ASSET_NAMES: Record<string, string> = {
  BTC: "Bitcoin",
  ETH: "Ethereum",
  SOL: "Solana",
  XRP: "XRP",
  ADA: "Cardano",
  DOT: "Polkadot",
  LINK: "Chainlink",
  LTC: "Litecoin",
};

export default function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null),
    [markets, setMarkets] = useState<Market[]>([]);
  const [view, setView] = useState<View>("overview"),
    [selected, setSelected] = useState("BTCUSDT"),
    [interval, setInterval] = useState("1h");
  const [analysis, setAnalysis] = useState<Analysis | null>(null),
    [portfolio, setPortfolio] = useState<Portfolio | null>(null),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("Ansluter till Odin Core …");
  const [amount, setAmount] = useState(1000),
    [sl, setSl] = useState(2),
    [tp, setTp] = useState(4);
  const [scanner, setScanner] = useState<ScannerItem[]>([]),
    [scanInterval, setScanInterval] = useState("1h"),
    [auto, setAuto] = useState<AutoSettings | null>(null),
    [cycle, setCycle] = useState<AutoCycle | null>(null),
    [performance, setPerformance] = useState<Performance | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]),
    [strategyEval, setStrategyEval] = useState<StrategyEvaluation | null>(null),
    [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exchange, setExchange] = useState<ExchangeConnection | null>(null);
  const [liveRisk, setLiveRisk] = useState<LiveRiskSettings | null>(null);
  const [livePreview, setLivePreview] = useState<LiveOrderPreview | null>(null);
  const [liveAccount, setLiveAccount] = useState<LiveAccount | null>(null);
  const [liveAccountLoading, setLiveAccountLoading] = useState(false);
  const [pairs, setPairs] = useState<TradingPair[]>([]);
  const [pairSearch, setPairSearch] = useState("");
  const [pairMenuOpen, setPairMenuOpen] = useState(false);
  const [selectedPairs, setSelectedPairs] = useState<string[]>([]);
  const [buyPair, setBuyPair] = useState("");
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [buyType, setBuyType] = useState<"market" | "limit">("market");
  const [amountMode, setAmountMode] = useState<"eur" | "crypto" | "percentage">(
    "eur",
  );
  const [sellPercentage, setSellPercentage] = useState<25 | 50 | 75 | 100>(25);
  const [buyAmount, setBuyAmount] = useState("");
  const [limitPrice, setLimitPrice] = useState("");
  const [slippage, setSlippage] = useState("1");
  const [lastLiveOrder, setLastLiveOrder] = useState<{
    exchange_order_id: string | null;
    status: string;
    submitted_at: string | null;
    symbol: string;
    side: string;
    order_type: string;
    quantity: number;
    amount_eur: number;
    submitted_price: number | null;
  } | null>(null);
  const [clock, setClock] = useState(() => Date.now());
  function runLoad(
    task: Promise<unknown>,
    fallback = "Kunde inte uppdatera data",
  ) {
    void task.catch((error) => {
      const friendlyMessage = getErrorMessage(error, fallback);
      setMessage(friendlyMessage);
      setErrorMessage(friendlyMessage);
    });
  }
  async function loadStatus() {
    try {
      setStatus(await api.getStatus());
      setErrorMessage(null);
      setMessage("Odin Core är ansluten");
    } catch (e) {
      const friendlyMessage = getErrorMessage(e, "Odin Core kunde inte nås.");
      setMessage(friendlyMessage);
      setErrorMessage(friendlyMessage);
    }
  }
  async function loadMarkets() {
    const data = await api.getMarkets();
    setMarkets(data.markets);
  }
  async function loadAnalysis() {
    setAnalysis(await api.getAnalysis(selected, interval));
  }
  async function loadPortfolio() {
    setPortfolio(await api.getPortfolio());
  }
  async function loadScanner() {
    const data = await api.getScanner(scanInterval);
    setScanner(data.items);
  }
  async function loadAuto() {
    setAuto(await api.getAutoSettings());
  }
  async function loadPerformance() {
    setPerformance(await api.getPerformance());
  }
  async function loadAI() {
    setAiAnalysis(await api.getAIAnalysis(selected, interval));
  }
  async function loadStrategies() {
    const data = await api.getStrategies();
    setStrategies(data);
    if (!editingStrategy && data.length) setEditingStrategy(data[0]);
  }
  async function loadLiveSettings() {
    const [connection, risk, discovered] = await Promise.all([
      api.getExchangeConnection(),
      api.getLiveRisk(),
      api.getTradingPairs(),
    ]);
    setExchange(connection);
    setLiveRisk(risk);
    setSelectedPairs(risk.allowed_pairs);
    if (!buyPair || !risk.allowed_pairs.includes(buyPair))
      setBuyPair(risk.allowed_pairs[0] ?? "");
    setPairs(discovered.pairs);
  }
  async function loadLiveAccount() {
    setLiveAccountLoading(true);
    try {
      setLiveAccount(await api.getLiveAccount());
    } finally {
      setLiveAccountLoading(false);
    }
  }
  async function saveStrategy() {
    if (!editingStrategy) return;
    const saved = await api.saveStrategy(editingStrategy);
    setEditingStrategy(saved);
    await loadStrategies();
  }
  async function activateStrategy(id: number) {
    await api.activateStrategy(id);
    await loadStrategies();
  }
  async function duplicateStrategy(id: number) {
    const copy = await api.duplicateStrategy(id);
    await loadStrategies();
    setEditingStrategy(copy);
  }
  async function evaluateCurrentStrategy() {
    if (!editingStrategy) return;
    setStrategyEval(
      await api.evaluateStrategy(editingStrategy.id, selected, interval),
    );
  }
  async function saveAuto(next: AutoSettings) {
    const saved = await api.saveAutoSettings(next);
    setAuto(saved);
  }
  async function runAuto() {
    if (busy) return;
    setBusy(true);
    try {
      const result = await api.runAutoCycle();
      setCycle(result);
      await Promise.all([
        loadScanner(),
        loadPortfolio(),
        loadPerformance(),
        loadAuto(),
      ]);
    } catch (e) {
      setMessage(getErrorMessage(e, "Auto-cykeln misslyckades"));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    removeLegacyInterfacePreferences();
    runLoad(loadStatus());
    runLoad(loadMarkets());
    runLoad(loadPortfolio());
    runLoad(loadScanner());
    const timer = window.setInterval(() => {
      runLoad(loadMarkets());
      if (view === "paper") runLoad(loadPortfolio());
    }, 15000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (view === "analysis")
      runLoad(loadAnalysis(), "Kunde inte hämta marknadsanalysen");
  }, [selected, interval, view]);
  useEffect(() => {
    if (view === "analysis" || view === "ai")
      runLoad(loadAI(), "Kunde inte hämta AI-analysen");
  }, [selected, interval, view]);
  useEffect(() => {
    if (view === "scanner")
      runLoad(loadScanner(), "Kunde inte uppdatera scannern");
  }, [view, scanInterval]);
  useEffect(() => {
    runLoad(loadAuto());
    runLoad(loadPerformance());
    runLoad(loadStrategies());
    runLoad(
      loadLiveSettings(),
      "Kunde inte läsa inställningarna för live-handel",
    );
  }, []);
  useEffect(() => {
    if (!auto?.enabled) return;
    const timer = window.setInterval(() => void runAuto(), 30000);
    return () => window.clearInterval(timer);
  }, [auto?.enabled]);
  useEffect(() => {
    const timer = window.setInterval(() => setClock(Date.now()), 30000);
    return () => window.clearInterval(timer);
  }, []);
  async function saveCredentials(form: HTMLFormElement) {
    const data = new FormData(form);
    const apiKey = String(data.get("api_key") ?? "");
    const apiSecret = String(data.get("api_secret") ?? "");
    setExchange(await api.saveKrakenCredentials(apiKey, apiSecret));
    form.reset();
    setMessage("Kraken-nyckeln validerades och sparades säkert");
  }
  async function saveRisk(form: HTMLFormElement) {
    const data = new FormData(form);
    const allowedPairs = liveRisk?.allowed_pairs ?? [];
    setLiveRisk(
      await api.saveLiveRisk({
        max_order_eur: Number(data.get("max_order_eur")),
        max_daily_eur: Number(data.get("max_daily_eur")),
        max_orders_daily: Number(data.get("max_orders_daily")),
        daily_loss_eur: Number(data.get("daily_loss_eur")),
        cooldown_seconds: Number(data.get("cooldown_seconds")),
        allowed_pairs: allowedPairs,
        pair_limits: allowedPairs.map((symbol) => {
          const index = pairs.findIndex((pair) => pair.symbol === symbol);
          const numberOrNull = (name: string) => {
            const value = String(data.get(`${name}_${index}`) ?? "");
            return value ? Number(value) : null;
          };
          return {
            symbol,
            enabled: data.get(`pair_enabled_${index}`) === "on",
            max_order_eur: numberOrNull("pair_order"),
            max_daily_eur: numberOrNull("pair_daily"),
            max_orders_daily: numberOrNull("pair_count"),
          };
        }),
        buy_only: data.get("buy_only") === "on",
        risk_warning_accepted: data.get("risk_warning_accepted") === "on",
      }),
    );
  }
  async function saveAllowedPairs(next: string[]) {
    if (!liveRisk) return;
    const saved = await api.saveLiveRisk({
      ...liveRisk,
      allowed_pairs: next,
      pair_limits: liveRisk.pair_limits,
    });
    setLiveRisk(saved);
    setSelectedPairs(saved.allowed_pairs);
    if (!saved.allowed_pairs.includes(buyPair))
      setBuyPair(saved.allowed_pairs[0] ?? "");
    setLivePreview(null);
  }
  async function enableLive(form: HTMLFormElement) {
    const phrase = String(new FormData(form).get("confirmation_phrase") ?? "");
    await api.enableLiveMode(phrase);
    form.reset();
    await loadStatus();
  }
  async function previewLive(form: HTMLFormElement) {
    const data = new FormData(form);
    setLivePreview(
      await api.previewLiveOrder({
        symbol: buyPair,
        side: orderSide,
        order_type: buyType,
        ...(orderSide === "buy" && amountMode === "eur"
          ? { amount_eur: Number(buyAmount) }
          : amountMode === "percentage"
            ? { sell_percentage: sellPercentage }
            : { amount_crypto: Number(buyAmount) }),
        ...(buyType === "limit" ? { limit_price: Number(limitPrice) } : {}),
        max_slippage_percent: Number(slippage),
      }),
    );
  }
  async function confirmLive() {
    if (!livePreview || busy) return;
    setBusy(true);
    try {
      const result = await api.confirmLiveOrder(
        livePreview.preview_id,
        livePreview.side,
      );
      setMessage(result.message);
      setLastLiveOrder(result);
      setLivePreview(null);
      await loadLiveAccount();
    } finally {
      setBusy(false);
    }
  }
  async function killLiveTrading() {
    await api.activateLiveKillSwitch();
    setLivePreview(null);
    await Promise.all([loadStatus(), loadLiveSettings()]);
    setMessage("Nödstoppet är aktivt. Nya riktiga ordrar är blockerade.");
  }
  async function changeMode(trading_mode: TradingMode) {
    setBusy(true);
    try {
      const next = await api.setMode(trading_mode);
      setStatus(next);
      setMessage(
        trading_mode === "paper"
          ? "Paper trading är aktiverat"
          : "Handelssystemet är avstängt",
      );
    } catch (e) {
      setErrorMessage(getErrorMessage(e, "Kunde inte ändra driftläge"));
    } finally {
      setBusy(false);
    }
  }
  async function enablePaperTrading() {
    await changeMode("paper");
  }
  async function order(side: "buy" | "sell") {
    setBusy(true);
    try {
      setPortfolio(await api.placeOrder(selected, side, amount, sl, tp));
      setView("paper");
    } catch (e) {
      setErrorMessage(getErrorMessage(e, "Ordern misslyckades"));
    } finally {
      setBusy(false);
    }
  }
  const strongest = useMemo(
    () => [...markets].sort((a, b) => b.change_percent - a.change_percent)[0],
    [markets],
  );
  const bestOpportunity = useMemo(() => scanner[0] ?? null, [scanner]);
  const marketMood = useMemo(() => {
    const positive = markets.filter((m) => m.change_percent > 1).length;
    const negative = markets.filter((m) => m.change_percent < -1).length;
    return positive > negative + 2
      ? "Positiv"
      : negative > positive + 2
        ? "Orolig"
        : "Lugn";
  }, [markets]);
  const signalClass = getSignalClass;
  const sellablePairs =
    liveRisk?.allowed_pairs.filter((symbol) => {
      const pair = pairs.find((item) => item.symbol === symbol);
      const balance = liveAccount?.balances.find(
        (item) => item.display_symbol === pair?.base_symbol,
      );
      return pair?.tradable && balance != null && balance.available > 0;
    }) ?? [];
  const manualOrderPairs =
    orderSide === "sell" ? sellablePairs : (liveRisk?.allowed_pairs ?? []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span>ᛟ</span>
          <div>
            <b>PROJECT ODIN</b>
            <small>AVANCERAD AI · ENKLA BESLUT</small>
          </div>
        </div>
        <nav>
          <button
            className={view === "live" ? "active" : ""}
            onClick={() => {
              setView("live");
              runLoad(loadLiveAccount(), "Kunde inte uppdatera livekontot");
            }}
          >
            Livekonto
          </button>
          <button
            className={view === "overview" ? "active" : ""}
            onClick={() => setView("overview")}
          >
            ⌂ Hem
          </button>
          <button
            className={view === "analysis" ? "active" : ""}
            onClick={() => setView("analysis")}
          >
            ▥ Marknaden
          </button>
          <button
            className={view === "paper" ? "active" : ""}
            onClick={() => {
              setView("paper");
              runLoad(loadPortfolio());
            }}
          >
            ▣ Mitt testkonto
          </button>
          <button
            className={view === "ai" ? "active" : ""}
            onClick={() => setView("ai")}
          >
            ✦ Odins råd
          </button>
          <button
            className={view === "performance" ? "active" : ""}
            onClick={() => {
              setView("performance");
              runLoad(loadPerformance());
            }}
          >
            ↗ Resultat
          </button>
          <div className="nav-divider">ANALYSVERKTYG</div>
          <button
            className={view === "scanner" ? "active" : ""}
            onClick={() => setView("scanner")}
          >
            Market Scanner
          </button>
          <button
            className={view === "strategies" ? "active" : ""}
            onClick={() => {
              setView("strategies");
              runLoad(loadStrategies());
            }}
          >
            Strategy Lab
          </button>
          <button
            className={view === "settings" ? "active" : ""}
            onClick={() => setView("settings")}
          >
            ⚙ Inställningar
          </button>
        </nav>
        <div className="core-state">
          <i className={status ? "online" : ""}></i>
          {message}
        </div>
      </aside>
      <main>
        <header>
          <div>
            <p className="eyebrow">ODIN ASSISTENT</p>
            <h1>
              {view === "overview"
                ? "Hem"
                : view === "analysis"
                  ? "Marknaden"
                  : view === "scanner"
                    ? "Market Scanner"
                    : view === "ai"
                      ? "Odins råd"
                      : view === "paper"
                        ? "Mitt testkonto"
                        : view === "performance"
                          ? "Resultat"
                          : view === "strategies"
                            ? "Strategy Lab"
                            : view === "live"
                              ? "Livekonto"
                              : "Inställningar"}
            </h1>
            <p>Project Odin v1.3.0 · Komplett gränssnitt</p>
          </div>
          <div className="header-actions">
            <button
              className="emergency-button"
              onClick={() =>
                runLoad(killLiveTrading(), "Kunde inte aktivera nödstoppet")
              }
            >
              NÖDSTOPP LIVE
            </button>
            <Badge className={`mode-badge ${status?.trading_mode ?? "off"}`}>
              {status?.trading_mode === "live"
                ? "LIVE · MANUELL BEKRÄFTELSE"
                : status?.trading_mode === "paper"
                  ? "TESTKONTO AKTIVT"
                  : "HANDEL AV"}
            </Badge>
          </div>
        </header>
        {!status && !errorMessage && (
          <LoadingState>Ansluter till Odin Core…</LoadingState>
        )}
        {errorMessage && <ErrorState>{errorMessage}</ErrorState>}
        {view === "overview" && (
          <>
            <section className="welcome-card panel">
              <div>
                <p className="eyebrow">DIN MARKNADSRAPPORT</p>
                <h2>Hej! Jag har analyserat marknaden.</h2>
                <p>
                  Marknaden känns <b>{marketMood.toLowerCase()}</b> just nu.{" "}
                  {bestOpportunity
                    ? `Min tydligaste möjlighet är ${bestOpportunity.display_symbol}.`
                    : "Jag letar fortfarande efter ett tydligt läge."}
                </p>
              </div>
              <Button
                variant="primary"
                onClick={() => {
                  setView("ai");
                  runLoad(loadAI(), "Kunde inte hämta AI-analysen");
                }}
              >
                Visa Odins råd
              </Button>
            </section>
            <section className="simple-grid">
              <Card className="traffic-card">
                <span
                  className={`traffic-light ${marketMood === "Positiv" ? "green" : marketMood === "Orolig" ? "red" : "yellow"}`}
                ></span>
                <div>
                  <p className="eyebrow">MARKNADEN IDAG</p>
                  <h2>{marketMood}</h2>
                  <p>
                    {marketMood === "Positiv"
                      ? "Fler marknader stiger tydligt än faller."
                      : marketMood === "Orolig"
                        ? "Flera marknader rör sig nedåt. Odin är extra försiktig."
                        : "Inga ovanligt starka rörelser dominerar just nu."}
                  </p>
                </div>
              </Card>
              <Card className="opportunity-card">
                <p className="eyebrow">BÄSTA MÖJLIGHETEN</p>
                <h2>
                  {bestOpportunity?.display_symbol ??
                    strongest?.display_symbol ??
                    "Söker…"}
                </h2>
                <strong className={signalClass(bestOpportunity?.chief_signal)}>
                  {bestOpportunity?.chief_signal ?? "AVVAKTA"}
                </strong>
                <p>
                  {bestOpportunity?.chief_summary ??
                    "Odin samlar in mer information innan ett råd visas."}
                </p>
                <div className="plain-facts">
                  <span>
                    Säkerhet <b>{bestOpportunity?.chief_confidence ?? "—"}%</b>
                  </span>
                  <span>
                    Risk <b>{bestOpportunity?.chief_risk_level ?? "—"}</b>
                  </span>
                </div>
                <button
                  className="why-button"
                  onClick={() => {
                    if (bestOpportunity) setSelected(bestOpportunity.symbol);
                    setView("analysis");
                  }}
                >
                  Varför?
                </button>
              </Card>
              <Card className="account-card">
                <p className="eyebrow">DITT TESTKONTO</p>
                <h2>{fmt(portfolio?.equity)} USDT</h2>
                <strong
                  className={
                    (portfolio?.total_pnl ?? 0) >= 0 ? "positive" : "negative"
                  }
                >
                  {(portfolio?.total_pnl ?? 0) >= 0 ? "+" : ""}
                  {fmt(portfolio?.total_pnl_percent)} %
                </strong>
                <p>
                  {portfolio?.positions.length ?? 0} öppna positioner · inga
                  riktiga pengar används.
                </p>
                <button className="why-button" onClick={() => setView("paper")}>
                  Öppna testkontot
                </button>
              </Card>
            </section>
            <section className="panel safety-strip">
              <div>
                <p className="eyebrow">AUTOPILOT</p>
                <h2>
                  {status?.trading_mode === "paper"
                    ? "Träningsläget är aktivt"
                    : "Odin handlar inte automatiskt"}
                </h2>
                <p>
                  {status?.trading_mode === "paper"
                    ? "Alla affärer sker med låtsaspengar och kan följas i beslutsloggen."
                    : "Du har full kontroll. Automatisk riktig handel är permanent avstängd."}
                </p>
              </div>
              {status?.trading_mode !== "paper" ? (
                <Button
                  variant="primary"
                  disabled={busy || status?.emergency_stop}
                  onClick={() => void enablePaperTrading()}
                >
                  Starta testkonto
                </Button>
              ) : (
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() => void changeMode("off")}
                >
                  Pausa testkonto
                </Button>
              )}
            </section>
          </>
        )}
        {view === "analysis" && (
          <section className="analysis-layout">
            <article className="panel watchlist">
              <div className="panel-title">
                <div>
                  <p className="eyebrow">WATCHLIST</p>
                  <h2>Marknader</h2>
                </div>
              </div>
              {markets.map((m) => (
                <button
                  key={m.symbol}
                  className={selected === m.symbol ? "watch active" : "watch"}
                  onClick={() => setSelected(m.symbol)}
                >
                  <b>{m.display_symbol}</b>
                  <span>{fmt(m.price, m.price < 1 ? 4 : 2)}</span>
                  <small
                    className={m.change_percent >= 0 ? "positive" : "negative"}
                  >
                    {m.change_percent >= 0 ? "+" : ""}
                    {fmt(m.change_percent)}%
                  </small>
                </button>
              ))}
            </article>
            <article className="panel analysis-main">
              <div className="panel-title">
                <div>
                  <p className="eyebrow">TECHNICAL ANALYSIS</p>
                  <h2>{analysis?.display_symbol ?? selected}</h2>
                </div>
                <IntervalSelector value={interval} onChange={setInterval} />
              </div>
              {analysis && (
                <>
                  <div
                    className={`decision-card ${signalClass(analysis.indicators.signal)}`}
                  >
                    <div>
                      <p className="eyebrow">ODINS FÖRSLAG</p>
                      <strong>{analysis.indicators.signal}</strong>
                      <p>{analysis.indicators.simple_explanation}</p>
                    </div>
                    <div className="decision-facts">
                      <span>
                        Säkerhet <b>{analysis.indicators.confidence}%</b>
                      </span>
                      <span>
                        Risk <b>{analysis.indicators.risk_level}</b>
                      </span>
                      <span>
                        Tidsram <b>{interval}</b>
                      </span>
                    </div>
                  </div>
                  {aiAnalysis && (
                    <div
                      className={`chief-inline ${signalClass(aiAnalysis.chief.verdict)}`}
                    >
                      <div>
                        <p className="eyebrow">CHIEF AI</p>
                        <h3>{aiAnalysis.chief.verdict}</h3>
                        <p>{aiAnalysis.chief.summary}</p>
                      </div>
                      <div className="chief-inline-stats">
                        <span>
                          AI Confidence <b>{aiAnalysis.chief.confidence}%</b>
                        </span>
                        <span>
                          AI Score <b>{aiAnalysis.chief.score}/100</b>
                        </span>
                        <span>
                          Föreslagen storlek{" "}
                          <b>{aiAnalysis.chief.position_size_percent}%</b>
                        </span>
                      </div>
                    </div>
                  )}
                  <PriceChart candles={analysis.candles} />
                  <div className="analysis-metrics">
                    <div>
                      <span>Senaste pris</span>
                      <strong>{fmt(analysis.candles.at(-1)?.close)}</strong>
                    </div>
                    <div>
                      <span>EMA 20</span>
                      <strong>{fmt(analysis.indicators.ema_20)}</strong>
                    </div>
                    <div>
                      <span>EMA 50</span>
                      <strong>{fmt(analysis.indicators.ema_50)}</strong>
                    </div>
                    <div>
                      <span>RSI 14</span>
                      <strong>{fmt(analysis.indicators.rsi_14, 1)}</strong>
                    </div>
                    <div>
                      <span>ATR 14</span>
                      <strong>{fmt(analysis.indicators.atr_14)}</strong>
                    </div>
                    <div>
                      <span>Odin Score</span>
                      <strong>{analysis.indicators.total_score}/100</strong>
                    </div>
                  </div>
                  <div className="trade-box">
                    <div>
                      <label>
                        Belopp USDT
                        <input
                          type="number"
                          value={amount}
                          onChange={(e) => setAmount(Number(e.target.value))}
                        />
                      </label>
                      <label>
                        Stop-loss %
                        <input
                          type="number"
                          value={sl}
                          onChange={(e) => setSl(Number(e.target.value))}
                        />
                      </label>
                      <label>
                        Take-profit %
                        <input
                          type="number"
                          value={tp}
                          onChange={(e) => setTp(Number(e.target.value))}
                        />
                      </label>
                    </div>
                    {status?.trading_mode !== "paper" &&
                      !status?.emergency_stop && (
                        <button
                          className="paper-enable-button"
                          disabled={busy}
                          onClick={() => void enablePaperTrading()}
                        >
                          AKTIVERA PAPER TRADING
                        </button>
                      )}
                    <button
                      className="buy-button"
                      disabled={
                        busy ||
                        status?.trading_mode !== "paper" ||
                        status?.emergency_stop
                      }
                      onClick={() => void order("buy")}
                    >
                      KÖP MED PAPER-SALDO
                    </button>
                    <small>
                      {status?.emergency_stop
                        ? "Nödstoppet är aktivt. Återställ det på översikten."
                        : status?.trading_mode === "paper"
                          ? "Paper trading är aktivt. Inga riktiga pengar används."
                          : "Aktivera Paper trading här eller på översikten."}
                    </small>
                  </div>
                  <div className="explanation">
                    <p className="eyebrow">VARFÖR?</p>
                    {analysis.indicators.explanation.map((x, i) => (
                      <p key={i}>• {x}</p>
                    ))}
                    {analysis.indicators.warnings.map((x, i) => (
                      <p className="warning" key={`w${i}`}>
                        ⚠ {x}
                      </p>
                    ))}
                  </div>
                </>
              )}
            </article>
          </section>
        )}

        {view === "scanner" && (
          <>
            <section className="panel scanner-controls">
              <div className="panel-title">
                <div>
                  <p className="eyebrow">AUTOMATED MARKET SCANNER</p>
                  <h2>Rankade handelsmöjligheter</h2>
                </div>
                <IntervalSelector
                  intervals={["15m", "1h", "4h", "1d"]}
                  value={scanInterval}
                  onChange={setScanInterval}
                />
              </div>
              <div className="auto-grid">
                <label>
                  Belopp per affär
                  <input
                    type="number"
                    value={auto?.amount_usdt ?? 1000}
                    onChange={(e) =>
                      auto &&
                      setAuto({ ...auto, amount_usdt: Number(e.target.value) })
                    }
                  />
                </label>
                <label>
                  Minsta säkerhet
                  <input
                    type="number"
                    value={auto?.minimum_confidence ?? 80}
                    onChange={(e) =>
                      auto &&
                      setAuto({
                        ...auto,
                        minimum_confidence: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Max positioner
                  <input
                    type="number"
                    value={auto?.max_open_positions ?? 3}
                    onChange={(e) =>
                      auto &&
                      setAuto({
                        ...auto,
                        max_open_positions: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Stop-loss %
                  <input
                    type="number"
                    value={auto?.stop_loss_percent ?? 2}
                    onChange={(e) =>
                      auto &&
                      setAuto({
                        ...auto,
                        stop_loss_percent: Number(e.target.value),
                      })
                    }
                  />
                </label>
                <label>
                  Take-profit %
                  <input
                    type="number"
                    value={auto?.take_profit_percent ?? 4}
                    onChange={(e) =>
                      auto &&
                      setAuto({
                        ...auto,
                        take_profit_percent: Number(e.target.value),
                      })
                    }
                  />
                </label>
              </div>
              <div className="scanner-actions">
                <button
                  className="refresh"
                  disabled={busy}
                  onClick={() =>
                    runLoad(loadScanner(), "Kunde inte uppdatera scannern")
                  }
                >
                  Scanna nu
                </button>
                <button
                  className={auto?.enabled ? "emergency" : "buy-button"}
                  disabled={busy || !auto || status?.trading_mode !== "paper"}
                  onClick={() =>
                    auto &&
                    runLoad(
                      saveAuto({
                        ...auto,
                        enabled: !auto.enabled,
                        interval: scanInterval,
                      }),
                      "Kunde inte spara inställningarna",
                    )
                  }
                >
                  {auto?.enabled ? "STOPPA AUTO PAPER" : "STARTA AUTO PAPER"}
                </button>
                <button
                  className="paper-enable-button"
                  disabled={busy || !auto?.enabled}
                  onClick={() => void runAuto()}
                >
                  Kör en cykel nu
                </button>
              </div>
              <small>
                Automatiken kör en scanner-cykel var 30:e sekund så länge appen
                är öppen. Endast paper-saldo används.
              </small>
              {cycle && (
                <div className="cycle-note">
                  <b>Senaste cykel:</b> {cycle.scanned} marknader · öppnade{" "}
                  {cycle.opened.length} · stängde {cycle.closed.length}
                </div>
              )}
            </section>
            <section className="panel">
              <div className="scanner-table scanner-head">
                <b>#</b>
                <b>Marknad</b>
                <b>Förslag</b>
                <b>Säkerhet</b>
                <b>Risk</b>
                <b>Odin Score</b>
                <b>Pris</b>
              </div>
              {scanner.map((item) => (
                <button
                  className="scanner-table scanner-row"
                  key={item.symbol}
                  onClick={() => {
                    setSelected(item.symbol);
                    setInterval(scanInterval);
                    setView("analysis");
                  }}
                >
                  <span>{item.rank}</span>
                  <b>{item.display_symbol}</b>
                  <strong className={signalClass(item.chief_signal)}>
                    {item.chief_signal}
                  </strong>
                  <span>{item.chief_confidence}%</span>
                  <span>{item.chief_risk_level}</span>
                  <span>{item.chief_score}/100</span>
                  <span>{fmt(item.price, item.price < 1 ? 4 : 2)}</span>
                </button>
              ))}
            </section>
          </>
        )}

        {view === "ai" && (
          <section className="ai-layout">
            <article className="panel ai-controls">
              <div>
                <p className="eyebrow">EXPLAINABLE MULTI-AGENT ENGINE</p>
                <h2>Odins AI-råd</h2>
                <p className="muted">
                  Välj marknad och tidsram. v0.7 använder transparenta lokala
                  analysmoduler. Nyhets- och makroagenter visas som offline
                  tills verifierade datakällor ansluts.
                </p>
              </div>
              <div className="ai-selectors">
                <select
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {markets.map((m) => (
                    <option key={m.symbol} value={m.symbol}>
                      {m.display_symbol}
                    </option>
                  ))}
                </select>
                <IntervalSelector value={interval} onChange={setInterval} />
                <button
                  className="refresh"
                  onClick={() =>
                    runLoad(loadAI(), "Kunde inte hämta AI-analysen")
                  }
                >
                  Analysera igen
                </button>
              </div>
            </article>
            {aiAnalysis && (
              <>
                <article
                  className={`panel chief-card ${signalClass(aiAnalysis.chief.verdict)}`}
                >
                  <div className="chief-main">
                    <p className="eyebrow">
                      CHIEF AI · {aiAnalysis.display_symbol} ·{" "}
                      {aiAnalysis.interval}
                    </p>
                    <h2>{aiAnalysis.chief.verdict}</h2>
                    <p>{aiAnalysis.chief.summary}</p>
                  </div>
                  <div className="chief-gauge">
                    <strong>{aiAnalysis.chief.confidence}%</strong>
                    <span>CONFIDENCE</span>
                  </div>
                  <div className="chief-facts">
                    <div>
                      <span>AI Score</span>
                      <b>{aiAnalysis.chief.score}/100</b>
                    </div>
                    <div>
                      <span>Risk</span>
                      <b>{aiAnalysis.chief.risk_level}</b>
                    </div>
                    <div>
                      <span>Paper-position</span>
                      <b>{aiAnalysis.chief.position_size_percent}%</b>
                    </div>
                  </div>
                </article>
                <div className="agent-grid">
                  {aiAnalysis.agents.map((agent) => (
                    <article
                      className={`panel agent-card ${agent.status === "OFFLINE" ? "offline" : ""}`}
                      key={agent.agent}
                    >
                      <div className="agent-head">
                        <div>
                          <p className="eyebrow">{agent.title}</p>
                          <h3>{agent.verdict}</h3>
                        </div>
                        <div className="agent-score">
                          <strong>
                            {agent.status === "OFFLINE" ? "—" : agent.score}
                          </strong>
                          <small>{agent.status}</small>
                        </div>
                      </div>
                      <p>{agent.summary}</p>
                      {agent.status !== "OFFLINE" && (
                        <div className="confidence-bar">
                          <span
                            style={{ width: `${agent.confidence}%` }}
                          ></span>
                        </div>
                      )}
                      <small>
                        {agent.status === "OFFLINE"
                          ? "Datakälla saknas"
                          : `${agent.confidence}% säkerhet`}
                      </small>
                      <div className="agent-evidence">
                        {agent.evidence.map((e, i) => (
                          <p key={i}>• {e}</p>
                        ))}
                        {agent.warnings.map((w, i) => (
                          <p className="warning" key={`w${i}`}>
                            ⚠ {w}
                          </p>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
                <article className="panel chief-reasoning">
                  <p className="eyebrow">VARFÖR CHIEF AI VALDE DETTA</p>
                  <h2>Sammanvägd bedömning</h2>
                  {aiAnalysis.chief.reasons.map((r, i) => (
                    <p key={i}>• {r}</p>
                  ))}
                  {aiAnalysis.chief.warnings.map((w, i) => (
                    <p className="warning" key={`cw${i}`}>
                      ⚠ {w}
                    </p>
                  ))}
                </article>
              </>
            )}
          </section>
        )}

        {view === "strategies" && (
          <section className="strategy-layout">
            <article className="panel strategy-list">
              <div className="panel-title">
                <div>
                  <p className="eyebrow">STRATEGY REGISTRY</p>
                  <h2>Strategier</h2>
                </div>
              </div>
              {strategies.map((strategy) => (
                <button
                  key={strategy.id}
                  className={`strategy-item ${editingStrategy?.id === strategy.id ? "selected" : ""}`}
                  onClick={() => {
                    setEditingStrategy(strategy);
                    setStrategyEval(null);
                  }}
                >
                  <div>
                    <b>{strategy.name}</b>
                    <small>
                      v{strategy.version} · {strategy.strategy_type}
                    </small>
                  </div>
                  <span
                    className={strategy.active ? "active-pill" : "muted-pill"}
                  >
                    {strategy.active ? "AKTIV" : "INAKTIV"}
                  </span>
                </button>
              ))}
            </article>
            {editingStrategy && (
              <article className="panel strategy-editor">
                <div className="panel-title">
                  <div>
                    <p className="eyebrow">STRATEGY EDITOR</p>
                    <h2>{editingStrategy.name}</h2>
                  </div>
                  <span>Version {editingStrategy.version}</span>
                </div>
                <div className="strategy-form">
                  <label>
                    Namn
                    <input
                      value={editingStrategy.name}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          name: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label className="wide">
                    Beskrivning
                    <textarea
                      value={editingStrategy.description}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          description: e.target.value,
                        })
                      }
                    />
                  </label>
                  <label>
                    Minsta Odin Score
                    <input
                      type="number"
                      value={Number(
                        editingStrategy.parameters.minimum_score ?? 65,
                      )}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          parameters: {
                            ...editingStrategy.parameters,
                            minimum_score: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    RSI köp från
                    <input
                      type="number"
                      value={Number(
                        editingStrategy.parameters.rsi_buy_min ?? 50,
                      )}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          parameters: {
                            ...editingStrategy.parameters,
                            rsi_buy_min: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    RSI köp till
                    <input
                      type="number"
                      value={Number(
                        editingStrategy.parameters.rsi_buy_max ?? 70,
                      )}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          parameters: {
                            ...editingStrategy.parameters,
                            rsi_buy_max: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    RSI sälj under
                    <input
                      type="number"
                      value={Number(
                        editingStrategy.parameters.rsi_sell_below ?? 42,
                      )}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          parameters: {
                            ...editingStrategy.parameters,
                            rsi_sell_below: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    Risk per affär %
                    <input
                      type="number"
                      step="0.1"
                      value={Number(
                        editingStrategy.risk_profile.risk_per_trade_percent ??
                          1,
                      )}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          risk_profile: {
                            ...editingStrategy.risk_profile,
                            risk_per_trade_percent: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                  <label>
                    Max positioner
                    <input
                      type="number"
                      value={Number(
                        editingStrategy.risk_profile.max_open_positions ?? 4,
                      )}
                      onChange={(e) =>
                        setEditingStrategy({
                          ...editingStrategy,
                          risk_profile: {
                            ...editingStrategy.risk_profile,
                            max_open_positions: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </label>
                </div>
                <div className="strategy-actions">
                  <button
                    className="refresh"
                    onClick={() =>
                      runLoad(saveStrategy(), "Kunde inte spara strategin")
                    }
                  >
                    Spara ny version
                  </button>
                  <button
                    className="paper-enable-button"
                    onClick={() =>
                      runLoad(
                        activateStrategy(editingStrategy.id),
                        "Kunde inte aktivera strategin",
                      )
                    }
                    disabled={
                      editingStrategy.active || !editingStrategy.enabled
                    }
                  >
                    Aktivera strategi
                  </button>
                  <button
                    className="refresh"
                    onClick={() =>
                      runLoad(
                        duplicateStrategy(editingStrategy.id),
                        "Kunde inte kopiera strategin",
                      )
                    }
                  >
                    Kopiera
                  </button>
                </div>
                <div className="strategy-test">
                  <div>
                    <select
                      value={selected}
                      onChange={(e) => setSelected(e.target.value)}
                    >
                      {markets.map((m) => (
                        <option key={m.symbol} value={m.symbol}>
                          {m.display_symbol}
                        </option>
                      ))}
                    </select>
                    <select
                      value={interval}
                      onChange={(e) => setInterval(e.target.value)}
                    >
                      {intervals.map((i) => (
                        <option key={i}>{i}</option>
                      ))}
                    </select>
                    <button
                      className="buy-button"
                      onClick={() =>
                        runLoad(
                          evaluateCurrentStrategy(),
                          "Kunde inte utvärdera strategin",
                        )
                      }
                    >
                      Testa strategin nu
                    </button>
                  </div>
                  {strategyEval && (
                    <div
                      className={`decision-card ${signalClass(strategyEval.signal)}`}
                    >
                      <div>
                        <p className="eyebrow">STRATEGY ENGINE</p>
                        <strong>{strategyEval.signal}</strong>
                        {strategyEval.reasons.map((reason, i) => (
                          <p key={i}>• {reason}</p>
                        ))}
                      </div>
                      <div className="decision-facts">
                        <span>
                          Poäng <b>{strategyEval.score}/100</b>
                        </span>
                        <span>
                          Säkerhet <b>{strategyEval.confidence}%</b>
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            )}
          </section>
        )}

        {view === "paper" && portfolio && (
          <>
            <section className="metrics">
              <article>
                <span>Kontanter</span>
                <strong>{fmt(portfolio.cash_balance)} USDT</strong>
              </article>
              <article>
                <span>Totalt värde</span>
                <strong>{fmt(portfolio.equity)} USDT</strong>
              </article>
              <article>
                <span>Resultat</span>
                <strong
                  className={portfolio.total_pnl >= 0 ? "positive" : "negative"}
                >
                  {portfolio.total_pnl >= 0 ? "+" : ""}
                  {fmt(portfolio.total_pnl)} USDT
                </strong>
              </article>
              <article>
                <span>Positioner</span>
                <strong>{portfolio.positions.length}</strong>
              </article>
            </section>
            <section className="panel">
              <div className="panel-title">
                <div>
                  <p className="eyebrow">OPEN POSITIONS</p>
                  <h2>Öppna positioner</h2>
                </div>
                <button
                  className="refresh"
                  onClick={() =>
                    runLoad(loadPortfolio(), "Kunde inte uppdatera testkontot")
                  }
                >
                  Uppdatera
                </button>
              </div>
              {portfolio.positions.length === 0 ? (
                <EmptyState>Inga öppna positioner ännu.</EmptyState>
              ) : (
                <div className="position-table">
                  {portfolio.positions.map((p) => (
                    <div className="position-row" key={p.id}>
                      <b>{p.symbol}</b>
                      <span>Ingång {fmt(p.entry_price)}</span>
                      <span>Nu {fmt(p.current_price)}</span>
                      <span
                        className={
                          p.unrealized_pnl >= 0 ? "positive" : "negative"
                        }
                      >
                        {p.unrealized_pnl >= 0 ? "+" : ""}
                        {fmt(p.unrealized_pnl)} USDT
                      </span>
                      <span>SL {fmt(p.stop_loss)}</span>
                      <span>TP {fmt(p.take_profit)}</span>
                      <button
                        disabled={busy}
                        onClick={() => {
                          setSelected(p.symbol);
                          void order("sell");
                        }}
                      >
                        Stäng
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </section>
            <section className="panel journal-panel">
              <p className="eyebrow">TRADING JOURNAL</p>
              <h2>Senaste paper-affärer</h2>
              {portfolio.trades.map((t) => (
                <div className="trade-row" key={t.id}>
                  <b className={t.side === "BUY" ? "positive" : "negative"}>
                    {t.side}
                  </b>
                  <span>{t.symbol}</span>
                  <span>{fmt(t.quantity, 6)}</span>
                  <span>@ {fmt(t.price)}</span>
                  <span>{new Date(t.created_at).toLocaleString("sv-SE")}</span>
                  <span
                    className={t.realized_pnl >= 0 ? "positive" : "negative"}
                  >
                    {t.realized_pnl
                      ? `${t.realized_pnl >= 0 ? "+" : ""}${fmt(t.realized_pnl)} USDT`
                      : "—"}
                  </span>
                </div>
              ))}
            </section>
          </>
        )}

        {view === "performance" && performance && (
          <>
            <section className="metrics">
              <article>
                <span>Stängda affärer</span>
                <strong>{performance.closed_trades}</strong>
                <small>Paper trading</small>
              </article>
              <article>
                <span>Träffsäkerhet</span>
                <strong>{fmt(performance.win_rate)} %</strong>
                <small>
                  {performance.winning_trades} vinster /{" "}
                  {performance.losing_trades} förluster
                </small>
              </article>
              <article>
                <span>Realiserat resultat</span>
                <strong
                  className={
                    performance.total_realized_pnl >= 0
                      ? "positive"
                      : "negative"
                  }
                >
                  {performance.total_realized_pnl >= 0 ? "+" : ""}
                  {fmt(performance.total_realized_pnl)} USDT
                </strong>
              </article>
              <article>
                <span>Profit Factor</span>
                <strong>
                  {performance.profit_factor == null
                    ? "—"
                    : fmt(performance.profit_factor)}
                </strong>
              </article>
            </section>
            <section className="panel">
              <p className="eyebrow">PERFORMANCE CENTER</p>
              <h2>Strategins första mätvärden</h2>
              <div className="performance-grid">
                <div>
                  <span>Genomsnittlig vinst</span>
                  <strong className="positive">
                    +{fmt(performance.average_win)} USDT
                  </strong>
                </div>
                <div>
                  <span>Genomsnittlig förlust</span>
                  <strong className="negative">
                    {fmt(performance.average_loss)} USDT
                  </strong>
                </div>
                <div>
                  <span>Vinnande affärer</span>
                  <strong>{performance.winning_trades}</strong>
                </div>
                <div>
                  <span>Förlorande affärer</span>
                  <strong>{performance.losing_trades}</strong>
                </div>
              </div>
              <p className="muted">
                Statistiken bygger endast på stängda paper-affärer. Ett litet
                antal affärer säger ännu inget säkert om strategins framtida
                resultat.
              </p>
            </section>
          </>
        )}

        {view === "live" && (
          <section className="panel live-account-page">
            <div className="section-heading">
              <div>
                <p className="eyebrow">KRAKEN SPOT · ENDAST LÄSNING</p>
                <h2>Livekonto</h2>
              </div>
              <Button
                variant="secondary"
                disabled={liveAccountLoading}
                onClick={() =>
                  runLoad(loadLiveAccount(), "Kunde inte uppdatera livekontot")
                }
              >
                {liveAccountLoading ? "Uppdaterar…" : "Uppdatera"}
              </Button>
            </div>
            {liveAccountLoading && !liveAccount && (
              <LoadingState>Hämtar saldon och ordrar…</LoadingState>
            )}
            {liveAccount && (
              <>
                {clock -
                  new Date(liveAccount.last_successful_refresh).getTime() >
                  60000 && (
                  <p className="warning">
                    Uppgifterna är äldre än en minut. Uppdatera innan du fattar
                    beslut.
                  </p>
                )}
                <div className="performance-grid">
                  <div>
                    <span>Uppskattat portföljvärde</span>
                    <strong>{fmt(liveAccount.total_estimated_eur)} EUR</strong>
                    <small>
                      Uppskattning, inte ett exakt realisationsvärde
                    </small>
                  </div>
                  <div>
                    <span>Tillgängligt EUR-saldo</span>
                    <strong>{fmt(liveAccount.available_eur)} EUR</strong>
                  </div>
                  <div>
                    <span>Senast uppdaterat</span>
                    <strong>
                      {new Date(
                        liveAccount.last_successful_refresh,
                      ).toLocaleString("sv-SE")}
                    </strong>
                  </div>
                </div>
                <h2>Tillgångar med saldo</h2>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Tillgång</th>
                        <th>Totalt</th>
                        <th>Tillgängligt</th>
                        <th>Reserverat</th>
                        <th>Uppskattat EUR-värde</th>
                        <th>Genomsnittligt inköpspris</th>
                        <th>Uppskattat orealiserat resultat</th>
                        <th>Pristidpunkt</th>
                        <th>Andel</th>
                      </tr>
                    </thead>
                    <tbody>
                      {liveAccount.balances.map((balance) => (
                        <tr key={balance.canonical_asset_id}>
                          <td>
                            <b>{balance.display_symbol}</b>
                            <small>{balance.canonical_asset_id}</small>
                          </td>
                          <td>{fmt(balance.total, 8)}</td>
                          <td>{fmt(balance.available, 8)}</td>
                          <td>{fmt(balance.reserved, 8)}</td>
                          <td>
                            {balance.estimated_eur_value === null
                              ? "Värde saknas"
                              : `≈ ${fmt(balance.estimated_eur_value)} EUR`}
                          </td>
                          <td>
                            {balance.average_acquisition_price_eur === null
                              ? "Inköpspris saknas"
                              : `${fmt(balance.average_acquisition_price_eur)} EUR`}
                          </td>
                          <td>
                            {balance.estimated_unrealized_pnl_eur === null
                              ? "—"
                              : `≈ ${fmt(balance.estimated_unrealized_pnl_eur)} EUR`}
                          </td>
                          <td>
                            {balance.price_timestamp
                              ? new Date(
                                  balance.price_timestamp,
                                ).toLocaleString("sv-SE")
                              : "Pristidpunkt saknas"}
                          </td>
                          <td>
                            {balance.allocation_percent === null
                              ? "—"
                              : `${fmt(balance.allocation_percent)} %`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {liveRisk && (
                  <div className="live-settings">
                    <p className="eyebrow">HANDELSURVAL</p>
                    <h2>Tillåtna kryptovalutor</h2>
                    <button
                      type="button"
                      className="multi-select-trigger"
                      onClick={() => setPairMenuOpen(!pairMenuOpen)}
                    >
                      {selectedPairs.length} valda
                    </button>
                    {pairMenuOpen && (
                      <div className="multi-select-menu">
                        <input
                          aria-label="Sök kryptovaluta"
                          value={pairSearch}
                          onChange={(event) =>
                            setPairSearch(event.target.value)
                          }
                          placeholder="Sök namn, symbol eller Kraken-ID"
                        />
                        <div className="multi-select-actions">
                          <button
                            type="button"
                            onClick={() =>
                              setSelectedPairs(
                                pairs
                                  .filter((pair) => pair.tradable)
                                  .map((pair) => pair.symbol),
                              )
                            }
                          >
                            Välj alla
                          </button>
                          <button
                            type="button"
                            onClick={() => setSelectedPairs([])}
                          >
                            Rensa
                          </button>
                          <button
                            type="button"
                            onClick={() =>
                              setSelectedPairs(
                                ["BTC/EUR", "ETH/EUR"].filter((symbol) =>
                                  pairs.some((pair) => pair.symbol === symbol),
                                ),
                              )
                            }
                          >
                            Återställ standard
                          </button>
                        </div>
                        <div className="multi-select-options">
                          {pairs
                            .filter((pair) => {
                              const haystack =
                                `${ASSET_NAMES[pair.base_symbol] ?? pair.base_symbol} ${pair.base_symbol} ${pair.symbol} ${pair.exchange_pair_id}`.toLowerCase();
                              return (
                                pair.tradable &&
                                haystack.includes(pairSearch.toLowerCase())
                              );
                            })
                            .map((pair) => (
                              <label key={pair.exchange_pair_id}>
                                <input
                                  type="checkbox"
                                  checked={selectedPairs.includes(pair.symbol)}
                                  onChange={() =>
                                    setSelectedPairs((current) =>
                                      current.includes(pair.symbol)
                                        ? current.filter(
                                            (item) => item !== pair.symbol,
                                          )
                                        : [...current, pair.symbol],
                                    )
                                  }
                                />
                                <span>
                                  <b>
                                    {ASSET_NAMES[pair.base_symbol] ??
                                      pair.base_symbol}
                                  </b>
                                  {" — "}
                                  {pair.symbol} · {pair.status} · min{" "}
                                  {fmt(pair.minimum_cost)} EUR
                                </span>
                              </label>
                            ))}
                        </div>
                        <Button
                          variant="primary"
                          disabled={selectedPairs.length === 0}
                          onClick={() =>
                            runLoad(
                              saveAllowedPairs(selectedPairs),
                              "Kunde inte spara tillåtna kryptovalutor",
                            )
                          }
                        >
                          Spara urval
                        </Button>
                      </div>
                    )}
                    <div className="selected-chips">
                      {selectedPairs.map((symbol) => (
                        <button
                          type="button"
                          key={symbol}
                          onClick={() =>
                            setSelectedPairs((current) =>
                              current.filter((item) => item !== symbol),
                            )
                          }
                        >
                          {symbol} ×
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {liveRisk && (
                  <div className="live-settings manual-buy">
                    <p className="eyebrow">RIKTIGA PENGAR · MANUELLT</p>
                    <h2>Manuell order</h2>
                    <form
                      onSubmit={(event) => {
                        event.preventDefault();
                        runLoad(
                          previewLive(event.currentTarget),
                          "Kunde inte förhandsgranska ordern",
                        );
                      }}
                    >
                      <label>
                        Sida
                        <select
                          aria-label="Ordersida"
                          value={orderSide}
                          onChange={(event) => {
                            const side = event.target.value as "buy" | "sell";
                            setOrderSide(side);
                            setAmountMode(side === "sell" ? "crypto" : "eur");
                            if (
                              side === "sell" &&
                              !sellablePairs.includes(buyPair)
                            )
                              setBuyPair(sellablePairs[0] ?? "");
                            if (
                              side === "buy" &&
                              !liveRisk.allowed_pairs.includes(buyPair)
                            )
                              setBuyPair(liveRisk.allowed_pairs[0] ?? "");
                            setLivePreview(null);
                          }}
                        >
                          <option value="buy">Köp</option>
                          <option value="sell">Sälj</option>
                        </select>
                      </label>
                      <label>
                        Kryptovaluta
                        <select
                          value={buyPair}
                          onChange={(event) => {
                            setBuyPair(event.target.value);
                            setLivePreview(null);
                          }}
                        >
                          {manualOrderPairs.map((symbol) => (
                            <option key={symbol}>{symbol}</option>
                          ))}
                        </select>
                      </label>
                      {orderSide === "sell" &&
                        manualOrderPairs.length === 0 && (
                          <p className="warning">
                            Ingen tillåten EUR-tillgång har ett positivt
                            tillgängligt saldo. Reserverat saldo kan inte
                            säljas.
                          </p>
                        )}
                      <label>
                        Ordertyp
                        <select
                          value={buyType}
                          onChange={(event) => {
                            setBuyType(
                              event.target.value as "market" | "limit",
                            );
                            setLivePreview(null);
                          }}
                        >
                          <option value="market">Marknadsorder</option>
                          <option value="limit">Limitorder</option>
                        </select>
                      </label>
                      <label>
                        Inmatningssätt
                        <select
                          value={amountMode}
                          onChange={(event) => {
                            setAmountMode(
                              event.target.value as
                                "eur" | "crypto" | "percentage",
                            );
                            setLivePreview(null);
                          }}
                        >
                          {orderSide === "buy" && (
                            <option value="eur">Belopp i EUR</option>
                          )}
                          <option value="crypto">Antal krypto</option>
                          {orderSide === "sell" && (
                            <option value="percentage">
                              Procent av tillgängligt saldo
                            </option>
                          )}
                        </select>
                      </label>
                      {amountMode !== "percentage" ? (
                        <label>
                          Belopp
                          <input
                            aria-label="Orderbelopp"
                            type="number"
                            min="0"
                            step="any"
                            required
                            value={buyAmount}
                            onChange={(event) => {
                              setBuyAmount(event.target.value);
                              setLivePreview(null);
                            }}
                          />
                        </label>
                      ) : (
                        <fieldset>
                          <legend>Andel av tillgängligt saldo</legend>
                          <div className="live-actions">
                            {([25, 50, 75, 100] as const).map((percentage) => (
                              <button
                                type="button"
                                key={percentage}
                                className={
                                  sellPercentage === percentage ? "active" : ""
                                }
                                onClick={() => {
                                  setSellPercentage(percentage);
                                  setLivePreview(null);
                                }}
                              >
                                {percentage} %
                              </button>
                            ))}
                          </div>
                        </fieldset>
                      )}
                      {buyType === "limit" && (
                        <label>
                          Limitpris
                          <input
                            type="number"
                            min="0"
                            step="any"
                            required
                            value={limitPrice}
                            onChange={(event) => {
                              setLimitPrice(event.target.value);
                              setLivePreview(null);
                            }}
                          />
                        </label>
                      )}
                      <label>
                        Högsta slippage (%)
                        <input
                          type="number"
                          min="0.1"
                          max="5"
                          step="0.1"
                          value={slippage}
                          onChange={(event) => {
                            setSlippage(event.target.value);
                            setLivePreview(null);
                          }}
                        />
                      </label>
                      <Button variant="primary" type="submit">
                        Förhandsgranska{" "}
                        {orderSide === "sell" ? "försäljning" : "köp"}
                      </Button>
                    </form>
                    <p className="warning">
                      Marknadspris, kostnad och intäkt är uppskattningar. Ingen
                      order skickas innan en separat bekräftelse. Reserverade
                      tillgångar ingår aldrig i säljbara belopp.
                    </p>
                  </div>
                )}
                {lastLiveOrder && (
                  <div className="live-settings">
                    <p className="eyebrow">ORDERRESULTAT</p>
                    <h2>Ordern har skickats – inte nödvändigtvis fyllts</h2>
                    <p>
                      Kraken-ID: {lastLiveOrder.exchange_order_id ?? "väntar"}
                    </p>
                    <p>
                      {lastLiveOrder.side} · {lastLiveOrder.symbol} ·{" "}
                      {lastLiveOrder.order_type} ·{" "}
                      {fmt(lastLiveOrder.quantity, 8)} ·{" "}
                      {fmt(lastLiveOrder.amount_eur)} EUR · status{" "}
                      {lastLiveOrder.status}
                    </p>
                    <p>
                      Skickad{" "}
                      {lastLiveOrder.submitted_at
                        ? new Date(lastLiveOrder.submitted_at).toLocaleString(
                            "sv-SE",
                          )
                        : "tidpunkt saknas"}
                      {lastLiveOrder.submitted_price != null
                        ? ` · pris ${fmt(lastLiveOrder.submitted_price)} EUR`
                        : " · marknadspris fastställs vid utförande"}
                    </p>
                    <div className="live-actions">
                      <Button
                        variant="secondary"
                        onClick={() =>
                          document
                            .querySelector(".live-account-page table")
                            ?.scrollIntoView()
                        }
                      >
                        Visa bland öppna ordrar
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={() =>
                          runLoad(
                            loadLiveAccount(),
                            "Kunde inte uppdatera Livekonto",
                          )
                        }
                      >
                        Uppdatera Livekonto
                      </Button>
                    </div>
                  </div>
                )}
                <h2>Öppna spotordrar</h2>
                {liveAccount.open_orders.length === 0 ? (
                  <EmptyState>Inga öppna spotordrar.</EmptyState>
                ) : (
                  <div className="table-wrap">
                    <table>
                      <tbody>
                        {liveAccount.open_orders.map((orderItem) => (
                          <tr key={orderItem.exchange_order_id}>
                            <td>{orderItem.symbol}</td>
                            <td>{orderItem.side}</td>
                            <td>{orderItem.order_type}</td>
                            <td>
                              {fmt(orderItem.filled_quantity, 8)} /{" "}
                              {fmt(orderItem.quantity, 8)}
                            </td>
                            <td>{orderItem.status}</td>
                            <td>
                              <Button
                                variant="secondary"
                                onClick={() => {
                                  if (
                                    window.confirm(
                                      `Avbryt den öppna ordern ${orderItem.exchange_order_id}?`,
                                    )
                                  )
                                    runLoad(
                                      api
                                        .cancelLiveOrder(
                                          orderItem.exchange_order_id,
                                        )
                                        .then(loadLiveAccount),
                                      "Kunde inte avbryta ordern",
                                    );
                                }}
                              >
                                Avbryt
                              </Button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <h2>Senaste slutförda och avbrutna ordrar</h2>
                <div className="table-wrap">
                  <table>
                    <tbody>
                      {liveAccount.recent_orders.map((orderItem) => (
                        <tr key={orderItem.exchange_order_id}>
                          <td>{orderItem.symbol}</td>
                          <td>{orderItem.side}</td>
                          <td>{orderItem.status}</td>
                          <td>{fmt(orderItem.filled_quantity, 8)}</td>
                          <td>
                            {orderItem.average_fill_price === null
                              ? "—"
                              : fmt(orderItem.average_fill_price)}
                          </td>
                          <td>
                            Avgift{" "}
                            {orderItem.fee === null
                              ? "saknas"
                              : fmt(orderItem.fee, 8)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h2>Senaste avslut och avgifter</h2>
                <div className="table-wrap">
                  <table>
                    <tbody>
                      {liveAccount.recent_fills.map((fill) => (
                        <tr key={fill.trade_id}>
                          <td>{fill.symbol}</td>
                          <td>{fill.side}</td>
                          <td>{fmt(fill.quantity, 8)}</td>
                          <td>{fmt(fill.price)}</td>
                          <td>
                            Avgift{" "}
                            {fill.fee === null ? "saknas" : fmt(fill.fee, 8)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        )}

        {view === "settings" && (
          <section className="panel settings-page">
            <p className="eyebrow">INSTÄLLNINGAR</p>
            <h2>Odins kompletta gränssnitt</h2>
            <div className="setting">
              <div>
                <b>Automatisk riktig handel</b>
                <small>
                  Är permanent avstängd. Varje riktig order kräver en ny
                  förhandsvisning och en aktiv manuell bekräftelse.
                </small>
              </div>
              <span>Permanent av</span>
            </div>
            <div className="setting">
              <div>
                <b>Testkonto</b>
                <small>
                  Du kan prova Odins råd med låtsaspengar utan ekonomisk risk.
                </small>
              </div>
              <span>{status?.trading_mode === "paper" ? "Aktivt" : "Av"}</span>
            </div>
            <div className="setting">
              <div>
                <b>Språk i appen</b>
                <small>
                  Tekniska värden, mätvärden och kontroller visas med tydliga
                  svenska förklaringar.
                </small>
              </div>
              <span>Svenska</span>
            </div>
            <div className="live-settings">
              <p className="eyebrow">KRAKEN SPOT</p>
              <h2>Säker anslutning</h2>
              <p>
                Minsta behörigheter: <b>Query Funds</b> och{" "}
                <b>Create &amp; modify orders</b>. Aktivera aldrig{" "}
                <b>Withdraw Funds</b>.
              </p>
              <p>Status: {exchange?.status ?? "kontrolleras…"}</p>
              {exchange?.warning && (
                <p className="warning">{exchange.warning}</p>
              )}
              <form
                autoComplete="off"
                onSubmit={(event) => {
                  event.preventDefault();
                  runLoad(
                    saveCredentials(event.currentTarget),
                    "Kunde inte ansluta Kraken",
                  );
                }}
              >
                <label>
                  API-nyckel
                  <input
                    name="api_key"
                    type="password"
                    required
                    autoComplete="off"
                  />
                </label>
                <label>
                  Privat API-nyckel
                  <input
                    name="api_secret"
                    type="password"
                    required
                    autoComplete="off"
                  />
                </label>
                <Button variant="primary" type="submit">
                  Validera och spara säkert
                </Button>
              </form>
              <div className="live-actions">
                <Button
                  variant="secondary"
                  onClick={() =>
                    runLoad(
                      api.testCredentialStore().then((result) => {
                        setMessage(result.message);
                        if (!result.available) {
                          setErrorMessage(result.message);
                        }
                      }),
                      "Kunde inte testa säker lagring",
                    )
                  }
                >
                  Testa säker lagring
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    runLoad(
                      api.testExchangeConnection().then(setExchange),
                      "Kunde inte testa Kraken-anslutningen",
                    )
                  }
                >
                  Testa anslutning
                </Button>
                <Button
                  variant="secondary"
                  onClick={() =>
                    runLoad(
                      api.deleteKrakenCredentials().then(async (next) => {
                        setExchange(next);
                        await Promise.all([loadStatus(), loadLiveSettings()]);
                      }),
                      "Kunde inte ta bort Kraken-nyckeln",
                    )
                  }
                >
                  Ta bort nyckel
                </Button>
              </div>
            </div>
            {liveRisk && (
              <div className="live-settings">
                <p className="eyebrow">RISKBARRIÄRER</p>
                <h2>Backend-enforced gränser</h2>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    runLoad(
                      saveRisk(event.currentTarget),
                      "Kunde inte spara riskgränser",
                    );
                  }}
                >
                  <fieldset className="pair-limits">
                    <legend>Valfria gränser per par</legend>
                    {pairs
                      .filter((pair) =>
                        liveRisk.allowed_pairs.includes(pair.symbol),
                      )
                      .map((pair) => {
                        const index = pairs.findIndex(
                          (item) => item.symbol === pair.symbol,
                        );
                        const limit = liveRisk.pair_limits.find(
                          (item) => item.symbol === pair.symbol,
                        );
                        return (
                          <div key={pair.symbol} className="pair-limit-row">
                            <b>{pair.symbol}</b>
                            <label>
                              <input
                                name={`pair_enabled_${index}`}
                                type="checkbox"
                                defaultChecked={limit?.enabled ?? true}
                              />{" "}
                              Aktivt
                            </label>
                            <input
                              aria-label={`${pair.symbol} högst per order`}
                              name={`pair_order_${index}`}
                              type="number"
                              placeholder="Högst/order EUR"
                              defaultValue={limit?.max_order_eur ?? ""}
                            />
                            <input
                              aria-label={`${pair.symbol} högst per dag`}
                              name={`pair_daily_${index}`}
                              type="number"
                              placeholder="Högst/dag EUR"
                              defaultValue={limit?.max_daily_eur ?? ""}
                            />
                            <input
                              aria-label={`${pair.symbol} högst antal`}
                              name={`pair_count_${index}`}
                              type="number"
                              placeholder="Antal/dag"
                              defaultValue={limit?.max_orders_daily ?? ""}
                            />
                          </div>
                        );
                      })}
                  </fieldset>
                  <label>
                    Högst per order (EUR)
                    <input
                      name="max_order_eur"
                      type="number"
                      min="1"
                      max="1000"
                      defaultValue={liveRisk.max_order_eur}
                    />
                  </label>
                  <label>
                    Högst per dag (EUR)
                    <input
                      name="max_daily_eur"
                      type="number"
                      min="1"
                      max="5000"
                      defaultValue={liveRisk.max_daily_eur}
                    />
                  </label>
                  <label>
                    Högst antal per dag
                    <input
                      name="max_orders_daily"
                      type="number"
                      min="1"
                      max="20"
                      defaultValue={liveRisk.max_orders_daily}
                    />
                  </label>
                  <label>
                    Daglig förlustgräns (EUR)
                    <input
                      name="daily_loss_eur"
                      type="number"
                      min="1"
                      max="1000"
                      defaultValue={liveRisk.daily_loss_eur}
                    />
                  </label>
                  <label>
                    Säkerhetspaus (sekunder)
                    <input
                      name="cooldown_seconds"
                      type="number"
                      min="60"
                      defaultValue={liveRisk.cooldown_seconds}
                    />
                  </label>
                  <label>
                    <input
                      name="buy_only"
                      type="checkbox"
                      defaultChecked={liveRisk.buy_only}
                    />{" "}
                    Endast köp
                  </label>
                  <label>
                    <input
                      name="risk_warning_accepted"
                      type="checkbox"
                      defaultChecked={liveRisk.risk_warning_accepted}
                    />{" "}
                    Jag förstår att riktiga pengar kan förloras
                  </label>
                  <Button variant="primary" type="submit">
                    Spara riskgränser
                  </Button>
                </form>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    runLoad(
                      enableLive(event.currentTarget),
                      "Kunde inte aktivera live-läget",
                    );
                  }}
                >
                  <label>
                    Skriv JAG FÖRSTÅR RISKEN
                    <input name="confirmation_phrase" autoComplete="off" />
                  </label>
                  <Button variant="secondary" type="submit">
                    Aktivera live med manuell bekräftelse
                  </Button>
                </form>
                {liveRisk.kill_switch_active && (
                  <Button
                    variant="secondary"
                    onClick={() =>
                      runLoad(
                        api.resetLiveKillSwitch().then(async (next) => {
                          setStatus(next);
                          await loadLiveSettings();
                        }),
                        "Kunde inte återställa nödstoppet",
                      )
                    }
                  >
                    Återställ nödstopp manuellt
                  </Button>
                )}
              </div>
            )}
          </section>
        )}
        {livePreview && (
          <div className="live-confirmation" role="dialog" aria-modal="true">
            <article className="panel">
              <p className="eyebrow">
                {livePreview.side === "sell"
                  ? "DETTA ÄR EN RIKTIG SÄLJORDER"
                  : "DETTA ÄR EN RIKTIG ORDER"}
              </p>
              <h2>
                {livePreview.side === "sell" ? "Sälj" : "Köp"}{" "}
                {livePreview.symbol} på Kraken
              </h2>
              <p>Exchange: Kraken</p>
              <p>Ordertyp: {livePreview.order_type}</p>
              <p>EUR-belopp: {fmt(livePreview.requested_amount)} EUR</p>
              <p>Kryptomängd: {fmt(livePreview.estimated_quantity, 8)}</p>
              <p>
                Aktuellt marknadspris: {fmt(livePreview.current_market_price)}{" "}
                EUR
              </p>
              {livePreview.order_type === "limit" && (
                <p>Limitpris: {fmt(livePreview.limit_price)} EUR</p>
              )}
              <p>Beräknad avgift: {fmt(livePreview.estimated_fee)} EUR</p>
              <p>Beräknad total: {fmt(livePreview.estimated_total)} EUR</p>
              <p>Tillgängligt EUR: {fmt(livePreview.available_eur)} EUR</p>
              {livePreview.side === "sell" && (
                <>
                  <p>
                    Tillgängligt före order:{" "}
                    {fmt(livePreview.available_crypto, 8)}
                  </p>
                  <p>
                    Beräknat saldo efter order:{" "}
                    {fmt(livePreview.available_crypto_after, 8)}
                  </p>
                  <p>
                    Andel av tillgängligt saldo:{" "}
                    {fmt(livePreview.sell_percentage)} %
                  </p>
                  <p>
                    Beräknad bruttointäkt:{" "}
                    {fmt(livePreview.estimated_gross_proceeds)} EUR
                  </p>
                  <p>
                    Beräknad nettointäkt:{" "}
                    {fmt(livePreview.estimated_net_proceeds)} EUR
                  </p>
                </>
              )}
              <p>
                Beräknat prisintervall: {fmt(livePreview.estimated_price_low)}–
                {fmt(livePreview.estimated_price_high)} EUR
              </p>
              <p>
                Pris hämtat{" "}
                {new Date(livePreview.price_timestamp).toLocaleString("sv-SE")}{" "}
                · giltig till{" "}
                {new Date(livePreview.expires_at).toLocaleString("sv-SE")}
              </p>
              <p>
                Riskgränser: högst {fmt(livePreview.maximum_order_eur)}{" "}
                EUR/order, slippage {fmt(livePreview.max_slippage_percent)} %.
              </p>
              <ul>
                {Object.entries(livePreview.applied_risk_limits).map(
                  ([name, value]) => (
                    <li key={name}>
                      {name}: {value == null ? "ej satt" : String(value)}
                    </li>
                  ),
                )}
              </ul>
              {livePreview.warnings.map((warning) => (
                <p className="warning" key={warning}>
                  {warning}
                </p>
              ))}
              <Button
                variant="primary"
                disabled={busy}
                onClick={() => void confirmLive()}
              >
                {livePreview.side === "sell"
                  ? "Bekräfta riktig försäljning"
                  : "Bekräfta riktigt köp"}
              </Button>
              <Button variant="secondary" onClick={() => setLivePreview(null)}>
                Avbryt
              </Button>
            </article>
          </div>
        )}
      </main>
    </div>
  );
}
