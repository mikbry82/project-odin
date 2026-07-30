from decimal import Decimal

import pytest

from app.exchanges.assets import normalize_asset
from app.exchanges.base import Credentials
from app.exchanges.kraken import KrakenProvider

PAIR_DATA = {
    "XXBTZEUR": {
        "wsname": "XBT/EUR",
        "base": "XXBT",
        "quote": "ZEUR",
        "ordermin": "0.0001",
        "costmin": "5",
        "pair_decimals": 1,
        "lot_decimals": 8,
        "status": "online",
    },
    "SOLEUR": {
        "wsname": "SOL/EUR",
        "base": "SOL",
        "quote": "ZEUR",
        "ordermin": "0.01",
        "costmin": "5",
        "pair_decimals": 3,
        "lot_decimals": 8,
        "status": "online",
    },
    "ADAEUR": {
        "wsname": "ADA/EUR",
        "base": "ADA",
        "quote": "ZEUR",
        "ordermin": "10",
        "costmin": "5",
        "pair_decimals": 5,
        "lot_decimals": 8,
        "status": "cancel_only",
    },
    "XETHZUSD": {
        "wsname": "ETH/USD",
        "base": "XETH",
        "quote": "ZUSD",
        "ordermin": "0.01",
        "costmin": "5",
        "pair_decimals": 2,
        "lot_decimals": 8,
        "status": "online",
    },
    "BTCUSDT.d": {
        "wsname": "XBT/USDT",
        "base": "XXBT",
        "quote": "USDT",
        "status": "online",
    },
}


@pytest.mark.asyncio
async def test_dynamic_pair_discovery_normalization_and_rules(monkeypatch) -> None:
    provider = KrakenProvider()
    calls = 0

    async def request(method, path, **kwargs):
        nonlocal calls
        calls += 1
        return PAIR_DATA

    monkeypatch.setattr(provider, "_request", request)
    pairs = await provider.fetch_pair_metadata()
    assert {item.symbol for item in pairs} == {
        "BTC/EUR",
        "SOL/EUR",
        "ADA/EUR",
        "ETH/USD",
    }
    assert [item.symbol for item in pairs if item.quote_symbol == "EUR" and item.tradable] == [
        "BTC/EUR",
        "SOL/EUR",
    ]
    btc = next(item for item in pairs if item.symbol == "BTC/EUR")
    assert btc.base_asset_id == "XXBT"
    assert btc.minimum_quantity == Decimal("0.0001")
    assert btc.minimum_cost == Decimal("5")
    assert btc.price_decimals == 1
    assert btc.quantity_decimals == 8
    await provider.fetch_pair_metadata()
    assert calls == 1
    await provider.fetch_pair_metadata(refresh=True)
    assert calls == 2


def test_asset_normalization_keeps_unknown_and_strips_variant() -> None:
    assert normalize_asset("XXBT").display_symbol == "BTC"
    assert normalize_asset("XBT").display_symbol == "BTC"
    assert normalize_asset("UNKNOWN.S").canonical_id == "UNKNOWN.S"
    assert normalize_asset("UNKNOWN.S").display_symbol == "UNKNOWN.S"


@pytest.mark.asyncio
async def test_balances_include_available_reserved_and_unknown(monkeypatch) -> None:
    provider = KrakenProvider()

    async def request(method, path, **kwargs):
        assert path == "/0/private/BalanceEx"
        return {
            "ZEUR": {"balance": "100", "hold_trade": "25"},
            "XXBT": {"balance": "0.5", "hold_trade": "0.1"},
            "UNKNOWN.S": {"balance": "7", "hold_trade": "0"},
        }

    monkeypatch.setattr(provider, "_request", request)
    balances = await provider.fetch_normalized_balances(Credentials("key", "secret"))
    eur = next(item for item in balances if item.display_symbol == "EUR")
    unknown = next(item for item in balances if item.display_symbol == "UNKNOWN.S")
    assert eur.available == Decimal("75")
    assert eur.reserved == Decimal("25")
    assert unknown.total == Decimal("7")
