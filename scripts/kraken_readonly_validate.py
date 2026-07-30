"""Manual read-only Kraken validation for v1.2.1.

This script has no call to place_spot_order and never prints balances or account values.
"""

import asyncio
import os
import sqlite3
import sys
from decimal import ROUND_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.exchanges.base import OrderRequest  # noqa: E402
from app.exchanges.kraken import KrakenProvider  # noqa: E402
from app.services.credential_store import credential_store  # noqa: E402


def desktop_database() -> Path:
    return Path(os.environ["APPDATA"]) / "Project Odin" / "project-odin.db"


def saved_allowlist() -> set[str]:
    path = desktop_database()
    if not path.exists():
        return {"BTC/EUR", "ETH/EUR"}
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        row = connection.execute(
            "SELECT allowed_pairs FROM live_risk_settings WHERE id = 1"
        ).fetchone()
        return set(row[0].split(",")) if row and row[0] else {"BTC/EUR", "ETH/EUR"}
    finally:
        connection.close()


async def main() -> int:
    capability = credential_store.capability(refresh=True)
    if not capability.available:
        print("Credential store: unavailable")
        return 2
    credentials = credential_store.load()
    if credentials is None:
        print("Kraken credentials: not configured")
        return 2
    provider = KrakenProvider()
    pairs = await provider.fetch_pair_metadata(refresh=True)
    eur_pairs = [pair for pair in pairs if pair.quote_symbol == "EUR" and pair.tradable]
    balances = [
        balance
        for balance in await provider.fetch_normalized_balances(credentials)
        if balance.total
    ]
    opened, recent = await provider.fetch_account_orders(credentials)
    fills = await provider.fetch_account_fills(credentials)
    print(f"Credential store: {capability.backend_class}")
    print(f"Tradable EUR spot pairs: {len(eur_pairs)}")
    print("Non-zero asset symbols: " + ", ".join(sorted(item.display_symbol for item in balances)))
    print(f"Open orders read: {len(opened)}")
    print(f"Recent orders read: {len(recent)}")
    print(f"Recent fills read: {len(fills)}")
    unpriced = [
        item.display_symbol
        for item in balances
        if item.display_symbol != "EUR"
        and not any(pair.base_symbol == item.display_symbol for pair in eur_pairs)
    ]
    print("Unpriced asset symbols: " + (", ".join(sorted(unpriced)) if unpriced else "none"))

    allowed = saved_allowlist()
    candidates = [pair for pair in eur_pairs if pair.symbol in allowed][:2]
    if len(candidates) < 2:
        print("Preview validation: fewer than two enabled EUR pairs")
        return 3
    for pair in candidates:
        price = await provider.fetch_current_price(pair.symbol)
        quantity = max(pair.minimum_quantity, pair.minimum_cost / price)
        quantity = quantity.quantize(Decimal(1).scaleb(-pair.quantity_decimals), rounding=ROUND_UP)
        await provider.preview_order(
            credentials,
            OrderRequest(
                symbol=pair.symbol,
                side="buy",
                order_type="limit",
                quantity=quantity,
                price=price,
                client_order_id="odinro" + os.urandom(6).hex(),
            ),
        )
        print(f"Validate-only preview passed: {pair.symbol}")
    print("No order submission method was called.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
