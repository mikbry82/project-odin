from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AutoTraderConfig(Base):
    __tablename__ = "auto_trader_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    interval: Mapped[str] = mapped_column(String(10), default="1h")
    amount_usdt: Mapped[float] = mapped_column(Float, default=1000.0)
    stop_loss_percent: Mapped[float] = mapped_column(Float, default=2.0)
    take_profit_percent: Mapped[float] = mapped_column(Float, default=4.0)
    minimum_confidence: Mapped[int] = mapped_column(Integer, default=80)
    max_open_positions: Mapped[int] = mapped_column(Integer, default=3)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
