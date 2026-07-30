from dataclasses import dataclass
from typing import Any

from app.services.indicators import analyse

DEFAULT_PARAMETERS: dict[str, Any] = {
    "ema_fast": 20,
    "ema_slow": 50,
    "rsi_buy_min": 50,
    "rsi_buy_max": 70,
    "rsi_sell_below": 42,
    "minimum_score": 65,
    "use_macd": True,
}

DEFAULT_RISK_PROFILE: dict[str, Any] = {
    "name": "Normal",
    "risk_per_trade_percent": 1.0,
    "max_open_positions": 4,
    "stop_loss_percent": 2.0,
    "take_profit_percent": 4.0,
}


@dataclass(frozen=True)
class StrategyDecision:
    signal: str
    score: int
    confidence: int
    reasons: list[str]


def merged_parameters(parameters: dict[str, Any] | None) -> dict[str, Any]:
    return {**DEFAULT_PARAMETERS, **(parameters or {})}


def evaluate_strategy(
    candles: list[dict], parameters: dict[str, Any] | None = None
) -> StrategyDecision:
    if len(candles) < 50:
        return StrategyDecision("AVVAKTA", 50, 50, ["För lite marknadsdata för ett säkert beslut."])

    p = merged_parameters(parameters)
    result = analyse(candles)
    score = int(result["total_score"])
    rsi = result.get("rsi_14")
    macd = result.get("macd_histogram")
    reasons: list[str] = []

    bullish = score >= int(p["minimum_score"])
    if rsi is not None:
        bullish = bullish and float(p["rsi_buy_min"]) <= rsi <= float(p["rsi_buy_max"])
        reasons.append(
            f"RSI är {rsi:.1f}; köpintervallet är {p['rsi_buy_min']}–{p['rsi_buy_max']}."
        )
    if bool(p.get("use_macd", True)) and macd is not None:
        bullish = bullish and macd > 0
        reasons.append(f"MACD-histogrammet är {'positivt' if macd > 0 else 'negativt'}.")

    bearish = score <= 40 or (rsi is not None and rsi < float(p["rsi_sell_below"]))
    if bullish:
        signal = "KÖP"
    elif bearish:
        signal = "SÄLJ"
    else:
        signal = "AVVAKTA"
    reasons.insert(0, f"Strategins sammanvägda poäng är {score}/100.")
    confidence = max(50, min(95, 50 + abs(score - 50)))
    return StrategyDecision(signal, score, confidence, reasons)
