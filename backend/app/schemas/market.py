from datetime import datetime

from pydantic import BaseModel, Field


class MarketTicker(BaseModel):
    symbol: str
    display_symbol: str
    price: float
    change_percent: float
    quote_volume: float
    source: str
    updated_at: datetime


class MarketOverviewResponse(BaseModel):
    markets: list[MarketTicker]
    source: str
    is_fallback: bool
    updated_at: datetime


class Candle(BaseModel):
    open_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorSnapshot(BaseModel):
    ema_20: float | None = None
    ema_50: float | None = None
    ema_200: float | None = None
    rsi_14: float | None = None
    atr_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    trend_score: int = Field(ge=0, le=100)
    momentum_score: int = Field(ge=0, le=100)
    volatility_score: int = Field(ge=0, le=100)
    total_score: int = Field(ge=0, le=100)
    signal: str
    confidence: int = Field(ge=0, le=100)
    risk_level: str
    simple_explanation: str
    warnings: list[str]
    explanation: list[str]


class MarketAnalysisResponse(BaseModel):
    symbol: str
    display_symbol: str
    interval: str
    candles: list[Candle]
    indicators: IndicatorSnapshot
    source: str
    is_fallback: bool
    updated_at: datetime
