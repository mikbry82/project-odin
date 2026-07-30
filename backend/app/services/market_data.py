from datetime import UTC, datetime

import httpx

SYMBOLS = (
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
    "ADAUSDT",
    "LINKUSDT",
    "AVAXUSDT",
    "DOGEUSDT",
    "SUIUSDT",
)
BASE_URL = "https://data-api.binance.vision"

FALLBACK = {
    "BTCUSDT": (64280.40, 2.31, 1_820_000_000.0),
    "ETHUSDT": (3482.18, 1.14, 940_000_000.0),
    "SOLUSDT": (171.52, 5.82, 610_000_000.0),
    "XRPUSDT": (0.6124, -0.74, 285_000_000.0),
    "BNBUSDT": (590.20, 0.82, 420_000_000.0),
    "ADAUSDT": (0.4021, 1.21, 180_000_000.0),
    "LINKUSDT": (13.84, 2.45, 210_000_000.0),
    "AVAXUSDT": (27.42, 3.10, 155_000_000.0),
    "DOGEUSDT": (0.1218, 0.54, 330_000_000.0),
    "SUIUSDT": (0.8420, 4.25, 145_000_000.0),
}


def _display_symbol(symbol: str) -> str:
    return f"{symbol[:-4]}/USDT"


def fallback_markets() -> list[dict]:
    now = datetime.now(UTC)
    return [
        {
            "symbol": symbol,
            "display_symbol": _display_symbol(symbol),
            "price": values[0],
            "change_percent": values[1],
            "quote_volume": values[2],
            "source": "demo-fallback",
            "updated_at": now,
        }
        for symbol, values in FALLBACK.items()
    ]


async def get_market_overview() -> tuple[list[dict], bool]:
    now = datetime.now(UTC)
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=6.0) as client:
            results: list[dict] = []
            for symbol in SYMBOLS:
                response = await client.get("/api/v3/ticker/24hr", params={"symbol": symbol})
                response.raise_for_status()
                payload = response.json()
                results.append(
                    {
                        "symbol": symbol,
                        "display_symbol": _display_symbol(symbol),
                        "price": float(payload["lastPrice"]),
                        "change_percent": float(payload["priceChangePercent"]),
                        "quote_volume": float(payload["quoteVolume"]),
                        "source": "binance-public",
                        "updated_at": now,
                    }
                )
            return results, False
    except (httpx.HTTPError, KeyError, TypeError, ValueError):
        return fallback_markets(), True


ALLOWED_INTERVALS = {"1m", "5m", "15m", "1h", "4h", "1d"}


def fallback_candles(symbol: str, limit: int = 240) -> list[dict]:
    import math
    from datetime import timedelta

    base = FALLBACK.get(symbol, FALLBACK["BTCUSDT"])[0]
    now = datetime.now(UTC)
    result = []
    previous = base * 0.94
    for index in range(limit):
        drift = index / max(limit - 1, 1) * base * 0.06
        wave = math.sin(index / 8) * base * 0.008
        close = base * 0.94 + drift + wave
        open_price = previous
        high = max(open_price, close) * 1.003
        low = min(open_price, close) * 0.997
        result.append(
            {
                "open_time": now - timedelta(minutes=limit - index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000 + index * 9,
            }
        )
        previous = close
    return result


async def get_candles(symbol: str, interval: str, limit: int = 240) -> tuple[list[dict], bool]:
    if symbol not in SYMBOLS:
        raise ValueError("Symbolen finns inte i Odins bevakningslista.")
    if interval not in ALLOWED_INTERVALS:
        raise ValueError("Tidsintervallet stöds inte.")
    limit = max(50, min(limit, 500))
    try:
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=8.0) as client:
            response = await client.get(
                "/api/v3/klines", params={"symbol": symbol, "interval": interval, "limit": limit}
            )
            response.raise_for_status()
            payload = response.json()
            candles = [
                {
                    "open_time": datetime.fromtimestamp(row[0] / 1000, UTC),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                }
                for row in payload
            ]
            return candles, False
    except (httpx.HTTPError, KeyError, TypeError, ValueError, IndexError):
        return fallback_candles(symbol, limit), True
