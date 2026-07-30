from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TradingMode(StrEnum):
    OFF = "off"
    PAPER = "paper"
    LIVE = "live"


class SystemState(Base):
    __tablename__ = "system_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    trading_mode: Mapped[str] = mapped_column(String(16), default=TradingMode.OFF.value)
    emergency_stop: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
