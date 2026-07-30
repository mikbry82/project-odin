"""Manual Kraken validation. This module is never imported by the test suite."""

import asyncio
import os
import sys
from decimal import ROUND_DOWN, Decimal
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from app.exchanges.base import OrderRequest  # noqa: E402
from app.exchanges.kraken import KrakenProvider  # noqa: E402
from app.services.credential_store import credential_store  # noqa: E402

ENABLE_FLAG = "ODIN_KRAKEN_MANUAL_SMOKE"
SUBMIT_PHRASE = "SKICKA KONTROLLERAD KRAKEN-ORDER"


async def main() -> int:
    if os.getenv(ENABLE_FLAG) != "I_UNDERSTAND_REAL_MONEY_RISK":
        print(
            f"Avbruten. Sätt {ENABLE_FLAG}=I_UNDERSTAND_REAL_MONEY_RISK "
            "endast för en övervakad manuell kontroll."
        )
        return 2
    credentials = credential_store.load()
    if credentials is None:
        print("Avbruten. Spara och validera Kraken-nyckeln i Project Odin först.")
        return 2
    provider = KrakenProvider()
    validation = await provider.validate_credentials(credentials)
    print(f"Anslutningsstatus: {validation.status.value}")
    print(f"Kontobehörighet: {'OK' if validation.account_access else 'saknas'}")
    if validation.warning:
        print(f"Varning: {validation.warning}")
    balances = await provider.fetch_balances(credentials)
    print(f"Tillgängliga saldon lästa: {len(balances)} tillgångar")
    symbol = "BTC/EUR"
    rules = await provider.fetch_symbol_rules(symbol)
    market_price = await provider.fetch_current_price(symbol)
    limit_price = (market_price * Decimal("0.50")).quantize(
        Decimal(1).scaleb(-rules.price_decimals), rounding=ROUND_DOWN
    )
    quantity = max(rules.minimum_quantity, Decimal("0.0001")).quantize(
        Decimal(1).scaleb(-rules.quantity_decimals), rounding=ROUND_DOWN
    )
    order = OrderRequest(
        symbol=symbol,
        side="buy",
        order_type="limit",
        quantity=quantity,
        price=limit_price,
        client_order_id="odin-smoke-" + os.urandom(4).hex(),
    )
    await provider.preview_order(credentials, order)
    print(
        f"Validerad förhandsvisning: köp {quantity} {symbol} "
        f"med limit {limit_price} EUR. Ingen order har skickats."
    )
    phrase = input(
        "Tryck Enter för att avsluta utan order, eller skriv exakt "
        f"'{SUBMIT_PHRASE}' för att skicka den riktiga limitordern: "
    )
    if phrase != SUBMIT_PHRASE:
        print("Avslutad utan riktig order.")
        return 0
    result = await provider.place_spot_order(credentials, order)
    print(f"Order skickad. Status: {result.status}.")
    print(f"Kraken order-ID: {result.exchange_order_id or 'saknas - kontrollera Kraken'}")
    print(
        "Avbryt testordern i Krakens gränssnitt, eller använd Project Odins "
        "'Avbryt alla öppna ordrar' efter att orderstatusen kontrollerats."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
