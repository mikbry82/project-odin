from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class CredentialInput(BaseModel):
    api_key: SecretStr = Field(min_length=8, max_length=256)
    api_secret: SecretStr = Field(min_length=16, max_length=512)


class ConnectionStatus(BaseModel):
    provider: Literal["kraken"] = "kraken"
    status: Literal["connected", "disconnected", "invalid_permissions", "unavailable"]
    account_access: bool = False
    order_access: bool | None = None
    withdrawal_access_absent: bool | None = None
    permission_verification_complete: bool = False
    warning: str | None = None


class CredentialStoreStatus(BaseModel):
    available: bool
    backend: str
    category: str | None = None
    message: str
    temporary_credential_deleted: bool


class PairLimit(BaseModel):
    symbol: str
    enabled: bool = True
    max_order_eur: float | None = Field(default=None, gt=0, le=1000)
    max_daily_eur: float | None = Field(default=None, gt=0, le=5000)
    max_orders_daily: int | None = Field(default=None, ge=1, le=20)


class RiskSettingsInput(BaseModel):
    max_order_eur: float = Field(gt=0, le=1000)
    max_daily_eur: float = Field(gt=0, le=5000)
    max_orders_daily: int = Field(ge=1, le=20)
    daily_loss_eur: float = Field(gt=0, le=1000)
    cooldown_seconds: int = Field(ge=60, le=86400)
    allowed_pairs: list[str]
    pair_limits: list[PairLimit] = Field(default_factory=list)
    buy_only: bool = True
    risk_warning_accepted: bool


class RiskSettingsResponse(RiskSettingsInput):
    kill_switch_active: bool


class TradingPairResponse(BaseModel):
    exchange_pair_id: str
    symbol: str
    base_asset_id: str
    base_symbol: str
    quote_asset_id: str
    quote_symbol: str
    minimum_quantity: float
    minimum_cost: float
    price_decimals: int
    quantity_decimals: int
    status: str
    tradable: bool
    allowed: bool


class PairDiscoveryResponse(BaseModel):
    pairs: list[TradingPairResponse]
    cached_for_seconds: int
    updated_at: datetime


class BalanceResponse(BaseModel):
    canonical_asset_id: str
    display_symbol: str
    total: float
    available: float
    reserved: float
    estimated_eur_value: float | None
    allocation_percent: float | None
    pricing_status: Literal["direct", "unpriced"]
    price_timestamp: datetime | None


class AccountOrderResponse(BaseModel):
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None
    filled_quantity: float
    average_fill_price: float | None
    fee: float | None
    status: str
    submitted_at: datetime | None
    updated_at: datetime | None


class AccountFillResponse(BaseModel):
    trade_id: str
    order_id: str | None
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float | None
    executed_at: datetime | None


class LiveAccountResponse(BaseModel):
    connection_status: str
    last_successful_refresh: datetime
    total_estimated_eur: float
    available_eur: float
    valuation_is_estimate: bool = True
    balances: list[BalanceResponse]
    open_orders: list[AccountOrderResponse]
    recent_orders: list[AccountOrderResponse]
    recent_fills: list[AccountFillResponse]


class LiveModeActivation(BaseModel):
    confirmation_phrase: str


class OrderPreviewInput(BaseModel):
    symbol: str
    side: Literal["buy"] = "buy"
    order_type: Literal["market", "limit"]
    amount_eur: float | None = Field(default=None, gt=0)
    amount_crypto: float | None = Field(default=None, gt=0)
    limit_price: float | None = Field(default=None, gt=0)
    recommendation_price: float | None = Field(default=None, gt=0)
    max_slippage_percent: float = Field(default=1.0, ge=0.1, le=5)


class OrderPreviewResponse(BaseModel):
    preview_id: str
    exchange: Literal["kraken"] = "kraken"
    symbol: str
    side: str
    order_type: str
    requested_amount: float
    estimated_quantity: float
    current_market_price: float
    limit_price: float | None
    estimated_total: float
    estimated_fee: float | None
    maximum_order_eur: float
    minimum_quantity: float
    minimum_cost: float
    quantity_decimals: int
    price_decimals: int
    pair_status: str
    price_timestamp: datetime
    available_eur: float
    max_slippage_percent: float
    estimated_price_low: float
    estimated_price_high: float
    applied_risk_limits: dict[str, float | int | bool | None]
    warnings: list[str]
    expires_at: datetime


class OrderConfirmationInput(BaseModel):
    preview_id: str
    confirmation_text: Literal["Bekräfta riktigt köp"]


class LiveOrderResponse(BaseModel):
    internal_order_id: str
    status: str
    exchange_order_id: str | None
    message: str
    submitted_at: datetime | None
    symbol: str
    order_type: str
    amount_eur: float
    submitted_price: float | None


class CancelAllInput(BaseModel):
    confirmation_text: Literal["Avbryt alla öppna ordrar"]


class CancelOrderInput(BaseModel):
    confirmation_text: Literal["Avbryt öppen order"]
