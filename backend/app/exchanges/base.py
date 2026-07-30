from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class CredentialStatus(StrEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    INVALID_PERMISSIONS = "invalid_permissions"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class Credentials:
    api_key: str
    api_secret: str


@dataclass(frozen=True)
class CredentialValidation:
    status: CredentialStatus
    account_access: bool
    order_access: bool | None
    withdrawal_access_absent: bool | None
    warning: str | None = None


@dataclass(frozen=True)
class SymbolRules:
    symbol: str
    base_asset: str
    quote_asset: str
    minimum_quantity: Decimal
    minimum_cost: Decimal
    price_decimals: int
    quantity_decimals: int
    status: str = "online"
    exchange_pair_id: str = ""


@dataclass(frozen=True)
class TradingPair:
    exchange_pair_id: str
    symbol: str
    base_asset_id: str
    base_symbol: str
    quote_asset_id: str
    quote_symbol: str
    minimum_quantity: Decimal
    minimum_cost: Decimal
    price_decimals: int
    quantity_decimals: int
    status: str
    tradable: bool


@dataclass(frozen=True)
class ExchangeBalance:
    canonical_asset_id: str
    display_symbol: str
    total: Decimal
    available: Decimal
    reserved: Decimal


@dataclass(frozen=True)
class AccountOrder:
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    limit_price: Decimal | None
    filled_quantity: Decimal
    average_fill_price: Decimal | None
    fee: Decimal | None
    status: str
    submitted_at: datetime | None
    updated_at: datetime | None


@dataclass(frozen=True)
class AccountFill:
    trade_id: str
    order_id: str | None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal | None
    executed_at: datetime | None


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    client_order_id: str


@dataclass(frozen=True)
class ExchangeOrder:
    exchange_order_id: str | None
    status: str
    raw_status: str


class ExchangeProvider(ABC):
    name: str

    @abstractmethod
    async def validate_credentials(self, credentials: Credentials) -> CredentialValidation: ...

    @abstractmethod
    async def fetch_balances(self, credentials: Credentials) -> dict[str, Decimal]: ...

    async def fetch_normalized_balances(self, credentials: Credentials) -> list[ExchangeBalance]:
        return [
            ExchangeBalance(asset, asset, total, total, Decimal("0"))
            for asset, total in (await self.fetch_balances(credentials)).items()
        ]

    @abstractmethod
    async def fetch_trading_pairs(self) -> list[str]: ...

    async def fetch_pair_metadata(self, *, refresh: bool = False) -> list[TradingPair]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_symbol_rules(self, symbol: str) -> SymbolRules: ...

    @abstractmethod
    async def fetch_current_price(self, symbol: str) -> Decimal: ...

    @abstractmethod
    async def preview_order(
        self, credentials: Credentials, order: OrderRequest
    ) -> Decimal | None: ...

    @abstractmethod
    async def place_spot_order(
        self, credentials: Credentials, order: OrderRequest
    ) -> ExchangeOrder: ...

    @abstractmethod
    async def fetch_order_status(
        self, credentials: Credentials, exchange_order_id: str
    ) -> ExchangeOrder: ...

    @abstractmethod
    async def find_order_by_client_id(
        self, credentials: Credentials, client_order_id: str
    ) -> ExchangeOrder | None: ...

    @abstractmethod
    async def cancel_open_order(self, credentials: Credentials, exchange_order_id: str) -> bool: ...

    @abstractmethod
    async def fetch_recent_fills(self, credentials: Credentials) -> list[dict[str, str]]: ...

    async def fetch_account_orders(
        self, credentials: Credentials
    ) -> tuple[list[AccountOrder], list[AccountOrder]]:
        return [], []

    async def fetch_account_fills(self, credentials: Credentials) -> list[AccountFill]:
        return []
