export type TradingMode = "off" | "paper" | "live";

export type SystemStatus = {
  trading_mode: TradingMode;
  operating_mode: "simulation" | "live_confirmation";
  emergency_stop: boolean;
  live_trading_available: boolean;
  updated_at: string | null;
};

export type ExchangeConnection = {
  provider: "kraken";
  status: "connected" | "disconnected" | "invalid_permissions" | "unavailable";
  account_access: boolean;
  order_access: boolean | null;
  withdrawal_access_absent: boolean | null;
  permission_verification_complete: boolean;
  warning: string | null;
};

export type CredentialStoreStatus = {
  available: boolean;
  backend: string;
  category: string | null;
  message: string;
  temporary_credential_deleted: boolean;
};

export type LiveRiskSettings = {
  max_order_eur: number;
  max_daily_eur: number;
  max_orders_daily: number;
  daily_loss_eur: number;
  cooldown_seconds: number;
  allowed_pairs: string[];
  pair_limits: PairLimit[];
  buy_only: boolean;
  risk_warning_accepted: boolean;
  kill_switch_active: boolean;
};

export type PairLimit = {
  symbol: string;
  enabled: boolean;
  max_order_eur: number | null;
  max_daily_eur: number | null;
  max_orders_daily: number | null;
};

export type TradingPair = {
  exchange_pair_id: string;
  symbol: string;
  base_asset_id: string;
  base_symbol: string;
  quote_asset_id: string;
  quote_symbol: string;
  minimum_quantity: number;
  minimum_cost: number;
  price_decimals: number;
  quantity_decimals: number;
  status: string;
  tradable: boolean;
  allowed: boolean;
};

export type PairDiscovery = {
  pairs: TradingPair[];
  cached_for_seconds: number;
  updated_at: string;
};

export type LiveBalance = {
  canonical_asset_id: string;
  display_symbol: string;
  total: number;
  available: number;
  reserved: number;
  estimated_eur_value: number | null;
  allocation_percent: number | null;
  pricing_status: "direct" | "unpriced";
  price_timestamp: string | null;
  average_acquisition_price_eur: number | null;
  estimated_unrealized_pnl_eur: number | null;
};

export type AccountOrder = {
  exchange_order_id: string;
  symbol: string;
  side: string;
  order_type: string;
  quantity: number;
  limit_price: number | null;
  filled_quantity: number;
  average_fill_price: number | null;
  fee: number | null;
  status: string;
  submitted_at: string | null;
  updated_at: string | null;
};

export type AccountFill = {
  trade_id: string;
  order_id: string | null;
  symbol: string;
  side: string;
  quantity: number;
  price: number;
  fee: number | null;
  executed_at: string | null;
};

export type LiveAccount = {
  connection_status: string;
  last_successful_refresh: string;
  total_estimated_eur: number;
  available_eur: number;
  valuation_is_estimate: true;
  balances: LiveBalance[];
  open_orders: AccountOrder[];
  recent_orders: AccountOrder[];
  recent_fills: AccountFill[];
};

export type LiveOrderPreview = {
  preview_id: string;
  exchange: "kraken";
  symbol: string;
  side: "buy" | "sell";
  order_type: "market" | "limit";
  requested_amount: number;
  estimated_quantity: number;
  current_market_price: number;
  limit_price: number | null;
  estimated_total: number;
  estimated_fee: number | null;
  maximum_order_eur: number;
  minimum_quantity: number;
  minimum_cost: number;
  quantity_decimals: number;
  price_decimals: number;
  pair_status: string;
  price_timestamp: string;
  available_eur: number;
  available_crypto: number | null;
  available_crypto_after: number | null;
  sell_percentage: number | null;
  estimated_gross_proceeds: number | null;
  estimated_net_proceeds: number | null;
  max_slippage_percent: number;
  estimated_price_low: number;
  estimated_price_high: number;
  applied_risk_limits: Record<string, number | boolean | null>;
  warnings: string[];
  expires_at: string;
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
  | "settings"
  | "live";
