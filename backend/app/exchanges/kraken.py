import base64
import binascii
import hashlib
import hmac
import time
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode

import httpx

from app.exchanges.assets import normalize_asset
from app.exchanges.base import (
    AccountFill,
    AccountOrder,
    Credentials,
    CredentialStatus,
    CredentialValidation,
    ExchangeBalance,
    ExchangeOrder,
    ExchangeProvider,
    OrderRequest,
    SymbolRules,
    TradingPair,
)
from app.exchanges.errors import (
    ExchangeError,
    ExchangeUnavailableError,
    InsufficientBalanceError,
    InvalidCredentialsError,
    MinimumOrderError,
    NonceError,
    RateLimitError,
)

KRAKEN_API = "https://api.kraken.com"
PAIR_CACHE_SECONDS = 3600


def _decimal(value: object, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def _timestamp(value: object) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(value), UTC)
    except (TypeError, ValueError, OSError):
        return None


class KrakenProvider(ExchangeProvider):
    name = "kraken"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._pairs: list[TradingPair] = []
        self._pairs_loaded_at = 0.0

    async def _request(
        self,
        method: str,
        path: str,
        *,
        credentials: Credentials | None = None,
        data: dict[str, str] | None = None,
    ) -> dict:
        payload = dict(data or {})
        headers: dict[str, str] = {}
        if credentials:
            nonce = str(time.time_ns())
            payload["nonce"] = nonce
            encoded = urlencode(payload)
            digest = hashlib.sha256((nonce + encoded).encode()).digest()
            try:
                secret = base64.b64decode(credentials.api_secret, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise InvalidCredentialsError() from exc
            signature = hmac.new(secret, path.encode() + digest, hashlib.sha512)
            headers = {
                "API-Key": credentials.api_key,
                "API-Sign": base64.b64encode(signature.digest()).decode(),
            }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=15)
        try:
            response = await client.request(
                method,
                f"{KRAKEN_API}{path}",
                params=payload if method == "GET" else None,
                data=payload if method != "GET" else None,
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ExchangeUnavailableError() from exc
        finally:
            if owns_client:
                await client.aclose()
        errors = body.get("error", [])
        if errors:
            joined = " ".join(errors)
            if any(
                text in joined for text in ("Invalid key", "Invalid signature", "Permission denied")
            ):
                raise InvalidCredentialsError()
            if "Insufficient funds" in joined:
                raise InsufficientBalanceError()
            if "Order minimum" in joined:
                raise MinimumOrderError()
            if "Rate limit" in joined or "Throttled" in joined:
                raise RateLimitError()
            if "Invalid nonce" in joined:
                raise NonceError()
            raise ExchangeError()
        return body.get("result", {})

    async def validate_credentials(self, credentials: Credentials) -> CredentialValidation:
        await self.fetch_normalized_balances(credentials)
        return CredentialValidation(
            status=CredentialStatus.CONNECTED,
            account_access=True,
            order_access=None,
            withdrawal_access_absent=None,
            warning=(
                "Kraken visar inte nyckelns fullständiga behörigheter via API. "
                "Kontrollera manuellt att endast Query Funds och Create & modify orders är aktiva."
            ),
        )

    async def fetch_pair_metadata(self, *, refresh: bool = False) -> list[TradingPair]:
        if (
            self._pairs
            and not refresh
            and time.monotonic() - self._pairs_loaded_at < PAIR_CACHE_SECONDS
        ):
            return list(self._pairs)
        result = await self._request("GET", "/0/public/AssetPairs")
        pairs: list[TradingPair] = []
        for pair_id, value in result.items():
            wsname = str(value.get("wsname") or "")
            if ".d" in pair_id.lower() or not wsname or "/" not in wsname:
                continue
            base_hint, quote_hint = wsname.split("/", 1)
            base = normalize_asset(str(value.get("base", base_hint)), base_hint)
            quote = normalize_asset(str(value.get("quote", quote_hint)), quote_hint)
            symbol = f"{base.display_symbol}/{quote.display_symbol}"
            status = str(value.get("status", "unknown"))
            pairs.append(
                TradingPair(
                    exchange_pair_id=pair_id,
                    symbol=symbol,
                    base_asset_id=base.canonical_id,
                    base_symbol=base.display_symbol,
                    quote_asset_id=quote.canonical_id,
                    quote_symbol=quote.display_symbol,
                    minimum_quantity=_decimal(value.get("ordermin")),
                    minimum_cost=_decimal(value.get("costmin")),
                    price_decimals=int(value.get("pair_decimals", 0)),
                    quantity_decimals=int(value.get("lot_decimals", 0)),
                    status=status,
                    tradable=status == "online",
                )
            )
        self._pairs = sorted(pairs, key=lambda item: item.symbol)
        self._pairs_loaded_at = time.monotonic()
        return list(self._pairs)

    async def _pair(self, symbol: str) -> TradingPair:
        pair = next(
            (item for item in await self.fetch_pair_metadata() if item.symbol == symbol), None
        )
        if pair is None:
            raise ExchangeError()
        return pair

    async def fetch_trading_pairs(self) -> list[str]:
        return [pair.symbol for pair in await self.fetch_pair_metadata() if pair.tradable]

    async def fetch_symbol_rules(self, symbol: str) -> SymbolRules:
        pair = await self._pair(symbol)
        return SymbolRules(
            symbol=pair.symbol,
            base_asset=pair.base_symbol,
            quote_asset=pair.quote_symbol,
            minimum_quantity=pair.minimum_quantity,
            minimum_cost=pair.minimum_cost,
            price_decimals=pair.price_decimals,
            quantity_decimals=pair.quantity_decimals,
            status=pair.status,
            exchange_pair_id=pair.exchange_pair_id,
        )

    async def fetch_normalized_balances(self, credentials: Credentials) -> list[ExchangeBalance]:
        try:
            result = await self._request("POST", "/0/private/BalanceEx", credentials=credentials)
        except ExchangeError:
            raw = await self._request("POST", "/0/private/Balance", credentials=credentials)
            result = {asset: {"balance": value} for asset, value in raw.items()}
        balances: list[ExchangeBalance] = []
        for asset_id, value in result.items():
            row = value if isinstance(value, dict) else {"balance": value}
            total = _decimal(row.get("balance"))
            reserved = max(_decimal(row.get("hold_trade")), Decimal("0"))
            available = max(total - reserved, Decimal("0"))
            asset = normalize_asset(asset_id)
            balances.append(
                ExchangeBalance(
                    asset.canonical_id, asset.display_symbol, total, available, reserved
                )
            )
        return balances

    async def fetch_balances(self, credentials: Credentials) -> dict[str, Decimal]:
        return {
            item.display_symbol: item.available
            for item in await self.fetch_normalized_balances(credentials)
        }

    async def fetch_current_price(self, symbol: str) -> Decimal:
        pair = await self._pair(symbol)
        result = await self._request(
            "GET", "/0/public/Ticker", data={"pair": pair.exchange_pair_id}
        )
        return _decimal(next(iter(result.values()))["c"][0])

    async def preview_order(self, credentials: Credentials, order: OrderRequest) -> Decimal | None:
        data = await self._order_data(order)
        data["validate"] = "true"
        await self._request("POST", "/0/private/AddOrder", credentials=credentials, data=data)
        return None

    async def place_spot_order(
        self, credentials: Credentials, order: OrderRequest
    ) -> ExchangeOrder:
        result = await self._request(
            "POST",
            "/0/private/AddOrder",
            credentials=credentials,
            data=await self._order_data(order),
        )
        transaction_ids = result.get("txid", [])
        return ExchangeOrder(
            exchange_order_id=transaction_ids[0] if transaction_ids else None,
            status="open",
            raw_status="submitted",
        )

    async def _order_data(self, order: OrderRequest) -> dict[str, str]:
        pair = await self._pair(order.symbol)
        data = {
            "pair": pair.exchange_pair_id,
            "type": order.side,
            "ordertype": order.order_type,
            "volume": str(order.quantity),
            "cl_ord_id": order.client_order_id,
        }
        if order.price is not None:
            data["price"] = str(order.price)
        return data

    def _account_order(
        self, order_id: str, value: dict, pair_by_id: dict[str, str]
    ) -> AccountOrder:
        description = value.get("descr", {})
        pair_value = str(description.get("pair", value.get("pair", "Okänt")))
        symbol = pair_by_id.get(pair_value, pair_value.replace("XBT", "BTC"))
        quantity = _decimal(value.get("vol"))
        filled = _decimal(value.get("vol_exec"))
        cost = _decimal(value.get("cost"))
        return AccountOrder(
            exchange_order_id=order_id,
            symbol=symbol,
            side=str(description.get("type", value.get("type", "unknown"))),
            order_type=str(description.get("ordertype", value.get("ordertype", "unknown"))),
            quantity=quantity,
            limit_price=_decimal(description.get("price")) or None,
            filled_quantity=filled,
            average_fill_price=(cost / filled if filled else None),
            fee=_decimal(value.get("fee")) or None,
            status=str(value.get("status", "unknown")),
            submitted_at=_timestamp(value.get("opentm")),
            updated_at=_timestamp(value.get("closetm") or value.get("lastupdated")),
        )

    async def fetch_account_orders(
        self, credentials: Credentials
    ) -> tuple[list[AccountOrder], list[AccountOrder]]:
        pairs = await self.fetch_pair_metadata()
        pair_by_id = {
            key: pair.symbol
            for pair in pairs
            for key in (
                pair.exchange_pair_id,
                pair.symbol,
                pair.symbol.replace("/", ""),
                pair.symbol.replace("BTC", "XBT"),
                pair.symbol.replace("BTC", "XBT").replace("/", ""),
            )
        }
        opened = await self._request("POST", "/0/private/OpenOrders", credentials=credentials)
        closed = await self._request(
            "POST", "/0/private/ClosedOrders", credentials=credentials, data={"trades": "true"}
        )
        open_orders = [
            self._account_order(order_id, value, pair_by_id)
            for order_id, value in opened.get("open", {}).items()
        ]
        recent = [
            self._account_order(order_id, value, pair_by_id)
            for order_id, value in closed.get("closed", {}).items()
        ][:50]
        return open_orders, recent

    async def fetch_account_fills(self, credentials: Credentials) -> list[AccountFill]:
        pairs = await self.fetch_pair_metadata()
        pair_by_id = {
            key: pair.symbol
            for pair in pairs
            for key in (
                pair.exchange_pair_id,
                pair.symbol,
                pair.symbol.replace("/", ""),
                pair.symbol.replace("BTC", "XBT"),
                pair.symbol.replace("BTC", "XBT").replace("/", ""),
            )
        }
        result = await self._request(
            "POST", "/0/private/TradesHistory", credentials=credentials, data={"type": "all"}
        )
        return [
            AccountFill(
                trade_id=trade_id,
                order_id=(str(value.get("ordertxid")) if value.get("ordertxid") else None),
                symbol=pair_by_id.get(str(value.get("pair")), str(value.get("pair", "Okänt"))),
                side=str(value.get("type", "unknown")),
                quantity=_decimal(value.get("vol")),
                price=_decimal(value.get("price")),
                fee=_decimal(value.get("fee")) or None,
                executed_at=_timestamp(value.get("time")),
            )
            for trade_id, value in list(result.get("trades", {}).items())[:50]
        ]

    async def fetch_recent_fills(self, credentials: Credentials) -> list[dict[str, str]]:
        return [
            {"id": item.trade_id, "status": "filled"}
            for item in await self.fetch_account_fills(credentials)
        ]

    async def fetch_order_status(
        self, credentials: Credentials, exchange_order_id: str
    ) -> ExchangeOrder:
        result = await self._request(
            "POST",
            "/0/private/QueryOrders",
            credentials=credentials,
            data={"txid": exchange_order_id},
        )
        order = result.get(exchange_order_id, {})
        raw = order.get("status", "unknown")
        status = {
            "pending": "open",
            "open": "open",
            "closed": "filled",
            "canceled": "cancelled",
            "expired": "cancelled",
        }.get(raw, "unknown_pending_reconciliation")
        if _decimal(order.get("vol_exec")) > 0 and raw == "open":
            status = "partially_filled"
        return ExchangeOrder(exchange_order_id, status, raw)

    async def find_order_by_client_id(
        self, credentials: Credentials, client_order_id: str
    ) -> ExchangeOrder | None:
        for path, collection in (
            ("/0/private/OpenOrders", "open"),
            ("/0/private/ClosedOrders", "closed"),
        ):
            result = await self._request("POST", path, credentials=credentials)
            for order_id, order in result.get(collection, {}).items():
                if order.get("cl_ord_id") == client_order_id:
                    raw = order.get("status", "unknown")
                    status = (
                        "partially_filled"
                        if collection == "open" and _decimal(order.get("vol_exec")) > 0
                        else (
                            "open"
                            if collection == "open"
                            else ("filled" if raw == "closed" else "cancelled")
                        )
                    )
                    return ExchangeOrder(order_id, status, raw)
        return None

    async def cancel_open_order(self, credentials: Credentials, exchange_order_id: str) -> bool:
        result = await self._request(
            "POST",
            "/0/private/CancelOrder",
            credentials=credentials,
            data={"txid": exchange_order_id},
        )
        return int(result.get("count", 0)) > 0
