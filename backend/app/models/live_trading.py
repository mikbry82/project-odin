from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LiveRiskSettings(Base):
    __tablename__ = "live_risk_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    max_order_eur: Mapped[float] = mapped_column(Float, default=10.0)
    max_daily_eur: Mapped[float] = mapped_column(Float, default=30.0)
    max_orders_daily: Mapped[int] = mapped_column(Integer, default=3)
    daily_loss_eur: Mapped[float] = mapped_column(Float, default=10.0)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60)
    allowed_pairs: Mapped[str] = mapped_column(String(128), default="BTC/EUR,ETH/EUR")
    buy_only: Mapped[bool] = mapped_column(Boolean, default=True)
    risk_warning_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PairRiskLimit(Base):
    __tablename__ = "pair_risk_limits"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_order_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_daily_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_orders_daily: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AssetCostBasis(Base):
    __tablename__ = "asset_cost_basis"

    canonical_asset_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    average_acquisition_price_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LiveOrder(Base):
    __tablename__ = "live_orders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    preview_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    client_order_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    exchange: Mapped[str] = mapped_column(String(16), default="kraken")
    exchange_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(20))
    side: Mapped[str] = mapped_column(String(8))
    order_type: Mapped[str] = mapped_column(String(16))
    requested_amount: Mapped[float] = mapped_column(Float)
    estimated_quantity: Mapped[float] = mapped_column(Float)
    preview_price: Mapped[float] = mapped_column(Float)
    estimated_total: Mapped[float] = mapped_column(Float)
    estimated_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl_eur: Mapped[float | None] = mapped_column(Float, nullable=True)
    submitted_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="previewed", index=True)
    exchange_response_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LiveOrderTransition(Base):
    __tablename__ = "live_order_transitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    live_order_id: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
