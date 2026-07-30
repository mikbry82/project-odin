export type TradingMode = "off" | "paper" | "live";

export type SystemStatus = {
  trading_mode: TradingMode;
  emergency_stop: boolean;
  live_trading_available: boolean;
  updated_at: string | null;
};

export type Market = {
  symbol: string;
  display_symbol: string;
  price: number;
  change_percent: number;
  quote_volume: number;
  source: string;
  updated_at: string;
};

export type MarketResponse = {
  markets: Market[];
  source: string;
  is_fallback: boolean;
  updated_at: string;
};

export type Candle = {
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type Indicators = {
  ema_20: number | null;
  ema_50: number | null;
  ema_200: number | null;
  rsi_14: number | null;
  atr_14: number | null;
  macd_histogram: number | null;
  trend_score: number;
  momentum_score: number;
  volatility_score: number;
  total_score: number;
  signal: string;
  confidence: number;
  risk_level: string;
  simple_explanation: string;
  warnings: string[];
  explanation: string[];
};

export type Analysis = {
  symbol: string;
  display_symbol: string;
  interval: string;
  candles: Candle[];
  indicators: Indicators;
  source: string;
  is_fallback: boolean;
  updated_at: string;
};

export type Position = {
  id: number;
  symbol: string;
  quantity: number;
  entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  stop_loss: number | null;
  take_profit: number | null;
  opened_at: string;
};

export type Trade = {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  realized_pnl: number;
  reason: string;
  created_at: string;
};

export type Portfolio = {
  starting_balance: number;
  cash_balance: number;
  equity: number;
  total_pnl: number;
  total_pnl_percent: number;
  positions: Position[];
  trades: Trade[];
};

export type ScannerItem = {
  rank: number;
  symbol: string;
  display_symbol: string;
  price: number;
  signal: string;
  confidence: number;
  risk_level: string;
  total_score: number;
  trend_score: number;
  momentum_score: number;
  volatility_score: number;
  simple_explanation: string;
  source: string;
  chief_signal: string;
  chief_score: number;
  chief_confidence: number;
  chief_risk_level: string;
  chief_summary: string;
};

export type ScannerResponse = {
  interval: string;
  items: ScannerItem[];
  updated_at: string;
};

export type AutoSettings = {
  enabled: boolean;
  interval: string;
  amount_usdt: number;
  stop_loss_percent: number;
  take_profit_percent: number;
  minimum_confidence: number;
  max_open_positions: number;
  last_run_at: string | null;
};

export type AutoCycle = {
  scanned: number;
  opened: string[];
  closed: string[];
  skipped: string[];
  message: string;
  run_at: string;
};

export type Performance = {
  closed_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_realized_pnl: number;
  average_win: number;
  average_loss: number;
  profit_factor: number | null;
};

export type AgentAssessment = {
  agent: string;
  title: string;
  verdict: string;
  score: number;
  confidence: number;
  status: string;
  summary: string;
  evidence: string[];
  warnings: string[];
};

export type AIAnalysis = {
  symbol: string;
  display_symbol: string;
  interval: string;
  price: number;
  source: string;
  agents: AgentAssessment[];
  chief: {
    verdict: string;
    score: number;
    confidence: number;
    risk_level: string;
    position_size_percent: number;
    summary: string;
    reasons: string[];
    warnings: string[];
  };
  generated_at: string;
};

export type Strategy = {
  id: number;
  name: string;
  description: string;
  strategy_type: string;
  version: number;
  enabled: boolean;
  active: boolean;
  parameters: Record<string, number | boolean | string>;
  risk_profile: Record<string, number | string>;
  created_at: string;
  updated_at: string;
};

export type StrategyEvaluation = {
  strategy_id: number;
  strategy_name: string;
  signal: string;
  score: number;
  confidence: number;
  reasons: string[];
  risk_profile: Record<string, number | string>;
};

export type View =
  | "overview"
  | "scanner"
  | "analysis"
  | "ai"
  | "strategies"
  | "paper"
  | "performance"
  | "settings";
