from datetime import datetime

from pydantic import BaseModel

from app.models.system_state import TradingMode


class SystemStatusResponse(BaseModel):
    trading_mode: TradingMode
    operating_mode: str
    emergency_stop: bool
    live_trading_available: bool = False
    updated_at: datetime | None = None


class TradingModeUpdate(BaseModel):
    trading_mode: TradingMode
