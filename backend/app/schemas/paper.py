from datetime import datetime

from pydantic import BaseModel, Field


class PaperOrderCreate(BaseModel):
    symbol: str
    side: str
    amount_usdt: float = Field(gt=0, le=100000)
    stop_loss_percent: float | None = Field(default=2.0, gt=0, le=50)
    take_profit_percent: float | None = Field(default=4.0, gt=0, le=200)


class PaperPositionResponse(BaseModel):
    id: int
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float
    stop_loss: float | None
    take_profit: float | None
    opened_at: datetime


class PaperTradeResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: float
    realized_pnl: float
    reason: str
    created_at: datetime


class PaperPortfolioResponse(BaseModel):
    starting_balance: float
    cash_balance: float
    equity: float
    total_pnl: float
    total_pnl_percent: float
    positions: list[PaperPositionResponse]
    trades: list[PaperTradeResponse]
