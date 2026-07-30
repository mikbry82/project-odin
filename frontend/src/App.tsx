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
  Market,
  Performance,
  Portfolio,
  ScannerItem,
  Strategy,
  StrategyEvaluation,
  SystemStatus,
  TradingMode,
  View,
} from "./types";
import { formatNumber as fmt, getErrorMessage, getSignalClass } from "./utils";

const intervals = INTERVALS;

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
  const [expertMode, setExpertMode] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
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
  }, []);
  useEffect(() => {
    if (!auto?.enabled) return;
    const timer = window.setInterval(() => void runAuto(), 30000);
    return () => window.clearInterval(timer);
  }, [auto?.enabled]);
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
          {expertMode && (
            <>
              <div className="nav-divider">EXPERTVERKTYG</div>
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
            </>
          )}
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
                            : "Inställningar"}
            </h1>
            <p>Project Odin v0.8.2 · Enkelt läge är standard</p>
          </div>
          <Badge className={`mode-badge ${status?.trading_mode ?? "off"}`}>
            {status?.trading_mode === "paper"
              ? "TESTKONTO AKTIVT"
              : "AUTOPILOT AV"}
          </Badge>
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
                    : "Du har full kontroll. Automatisk riktig handel är fortfarande låst."}
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

        {view === "settings" && (
          <section className="panel settings-page">
            <p className="eyebrow">INSTÄLLNINGAR</p>
            <h2>Gör Odin lagom enkel för dig</h2>
            <div className="setting">
              <div>
                <b>Expertläge</b>
                <small>
                  Visar tekniska verktyg som Market Scanner och Strategy Lab.
                  Enkelt läge rekommenderas för de flesta.
                </small>
              </div>
              <button
                className={expertMode ? "toggle on" : "toggle"}
                onClick={() => setExpertMode(!expertMode)}
              >
                {expertMode ? "På" : "Av"}
              </button>
            </div>
            <div className="setting">
              <div>
                <b>Automatisk riktig handel</b>
                <small>
                  Förblir låst tills testnet, riskmotor och fullständig
                  säkerhetskontroll är klara.
                </small>
              </div>
              <span>Låst</span>
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
                  Tekniska värden visas bara när du själv väljer att se dem.
                </small>
              </div>
              <span>Enkel svenska</span>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
