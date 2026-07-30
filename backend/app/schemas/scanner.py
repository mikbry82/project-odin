from datetime import datetime

from pydantic import BaseModel, Field


class ScannerItem(BaseModel):
    rank: int
    symbol: str
    display_symbol: str
    price: float
    signal: str
    confidence: int
    risk_level: str
    total_score: int
    trend_score: int
    momentum_score: int
    volatility_score: int
    simple_explanation: str
    source: str
    chief_signal: str
    chief_score: int
    chief_confidence: int
    chief_risk_level: str
    chief_summary: str


class ScannerResponse(BaseModel):
    interval: str
    items: list[ScannerItem]
    updated_at: datetime


class AutoTraderSettingsUpdate(BaseModel):
    enabled: bool
    interval: str = "1h"
    amount_usdt: float = Field(default=1000.0, gt=0, le=100000)
    stop_loss_percent: float = Field(default=2.0, gt=0, le=50)
    take_profit_percent: float = Field(default=4.0, gt=0, le=200)
    minimum_confidence: int = Field(default=80, ge=50, le=95)
    max_open_positions: int = Field(default=3, ge=1, le=10)


class AutoTraderSettingsResponse(AutoTraderSettingsUpdate):
    last_run_at: datetime | None = None


class AutoTraderCycleResponse(BaseModel):
    scanned: int
    opened: list[str]
    closed: list[str]
    skipped: list[str]
    message: str
    run_at: datetime


class PerformanceResponse(BaseModel):
    closed_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_realized_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float | None
