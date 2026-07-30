import asyncio

from app.services.ai_engine import run_ai_engine
from app.services.indicators import analyse
from app.services.market_data import SYMBOLS, get_candles


async def analyse_symbol(symbol: str, interval: str) -> dict:
    candles, is_fallback = await get_candles(symbol, interval, 240)
    indicators = analyse(candles)
    ai_result = run_ai_engine(candles)
    latest = float(candles[-1]["close"])
    chief = ai_result["chief"]
    return {
        "symbol": symbol,
        "display_symbol": f"{symbol[:-4]}/USDT",
        "price": latest,
        **indicators,
        "chief_signal": chief["verdict"],
        "chief_score": chief["score"],
        "chief_confidence": chief["confidence"],
        "chief_risk_level": chief["risk_level"],
        "chief_summary": chief["summary"],
        "source": "demo-fallback" if is_fallback else "binance-public",
    }


async def scan_markets(interval: str = "1h") -> list[dict]:
    results = await asyncio.gather(
        *(analyse_symbol(symbol, interval) for symbol in SYMBOLS),
        return_exceptions=True,
    )
    valid = [result for result in results if isinstance(result, dict)]
    valid.sort(
        key=lambda item: (
            item["signal"] in {"STARKT KÖP", "KÖP"},
            item["total_score"],
            item["confidence"],
        ),
        reverse=True,
    )
    for index, item in enumerate(valid, start=1):
        item["rank"] = index
    return valid
