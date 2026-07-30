from __future__ import annotations

from collections.abc import Sequence


def ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    multiplier = 2 / (period + 1)
    for price in values[period:]:
        value = (price - value) * multiplier + value
    return value


def ema_series(values: Sequence[float], period: int) -> list[float]:
    if len(values) < period:
        return []
    result = [sum(values[:period]) / period]
    multiplier = 2 / (period + 1)
    for price in values[period:]:
        result.append((price - result[-1]) * multiplier + result[-1])
    return result


def rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:], strict=True):
        average_gain = ((average_gain * (period - 1)) + gain) / period
        average_loss = ((average_loss * (period - 1)) + loss) / period
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def atr(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14
) -> float | None:
    if len(closes) <= period:
        return None
    true_ranges = []
    for index in range(1, len(closes)):
        true_ranges.append(
            max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            )
        )
    value = sum(true_ranges[:period]) / period
    for true_range in true_ranges[period:]:
        value = ((value * (period - 1)) + true_range) / period
    return value


def macd(values: Sequence[float]) -> tuple[float | None, float | None, float | None]:
    if len(values) < 35:
        return None, None, None
    fast = ema_series(values, 12)
    slow = ema_series(values, 26)
    offset = len(fast) - len(slow)
    line = [fast[index + offset] - slow[index] for index in range(len(slow))]
    signal = ema(line, 9)
    if signal is None:
        return line[-1], None, None
    return line[-1], signal, line[-1] - signal


def analyse(candles: list[dict]) -> dict:
    closes = [float(candle["close"]) for candle in candles]
    highs = [float(candle["high"]) for candle in candles]
    lows = [float(candle["low"]) for candle in candles]
    latest = closes[-1]
    ema20, ema50, ema200 = ema(closes, 20), ema(closes, 50), ema(closes, 200)
    rsi14 = rsi(closes)
    atr14 = atr(highs, lows, closes)
    macd_value, macd_signal, macd_histogram = macd(closes)

    trend_points = 50
    explanations: list[str] = []
    if ema20 is not None:
        trend_points += 15 if latest > ema20 else -15
        explanations.append(f"Priset ligger {'över' if latest > ema20 else 'under'} EMA 20.")
    if ema50 is not None:
        trend_points += 15 if latest > ema50 else -15
        explanations.append(f"Priset ligger {'över' if latest > ema50 else 'under'} EMA 50.")
    if ema20 is not None and ema50 is not None:
        trend_points += 10 if ema20 > ema50 else -10
    if ema200 is not None:
        trend_points += 10 if latest > ema200 else -10

    momentum_points = 50
    if rsi14 is not None:
        if 50 <= rsi14 <= 70:
            momentum_points += 25
            explanations.append(
                f"RSI {rsi14:.1f} visar positivt momentum utan tydligt överköpt läge."
            )
        elif rsi14 > 70:
            momentum_points += 5
            explanations.append(
                f"RSI {rsi14:.1f} är högt; momentum är starkt men rekylrisken ökar."
            )
        elif rsi14 < 30:
            momentum_points -= 5
            explanations.append(f"RSI {rsi14:.1f} är lågt och marknaden kan vara översåld.")
        else:
            momentum_points -= 15
    if macd_histogram is not None:
        momentum_points += 20 if macd_histogram > 0 else -20
        explanations.append(
            f"MACD-histogrammet är {'positivt' if macd_histogram > 0 else 'negativt'}."
        )

    volatility_points = 50
    if atr14 is not None and latest:
        atr_percent = atr14 / latest * 100
        if atr_percent < 1:
            volatility_points = 65
        elif atr_percent < 3:
            volatility_points = 80
        elif atr_percent < 6:
            volatility_points = 55
        else:
            volatility_points = 30
        explanations.append(f"ATR motsvarar cirka {atr_percent:.2f} % av priset.")

    trend_score = max(0, min(100, round(trend_points)))
    momentum_score = max(0, min(100, round(momentum_points)))
    volatility_score = max(0, min(100, round(volatility_points)))
    total_score = round(trend_score * 0.5 + momentum_score * 0.35 + volatility_score * 0.15)
    warnings: list[str] = []
    if rsi14 is not None and rsi14 >= 72:
        warnings.append("RSI är högt. Risken för en kortsiktig rekyl är förhöjd.")
    if rsi14 is not None and rsi14 <= 28:
        warnings.append("RSI är mycket lågt. Nedgången kan fortsätta trots översålt läge.")
    atr_percent = (atr14 / latest * 100) if atr14 is not None and latest else 0
    if atr_percent >= 4:
        warnings.append("Volatiliteten är hög och priset kan röra sig snabbt.")

    bullish_confirmations = sum(
        [
            latest > ema20 if ema20 else False,
            latest > ema50 if ema50 else False,
            macd_histogram > 0 if macd_histogram is not None else False,
            50 <= rsi14 < 70 if rsi14 is not None else False,
        ]
    )
    bearish_confirmations = sum(
        [
            latest < ema20 if ema20 else False,
            latest < ema50 if ema50 else False,
            macd_histogram < 0 if macd_histogram is not None else False,
            30 < rsi14 < 50 if rsi14 is not None else False,
        ]
    )
    if total_score >= 80 and bullish_confirmations >= 3 and not (rsi14 is not None and rsi14 >= 75):
        signal = "STARKT KÖP"
    elif (
        total_score >= 65 and bullish_confirmations >= 2 and not (rsi14 is not None and rsi14 >= 75)
    ):
        signal = "KÖP"
    elif total_score <= 25 and bearish_confirmations >= 3:
        signal = "STARKT SÄLJ"
    elif total_score <= 40 and bearish_confirmations >= 2:
        signal = "SÄLJ"
    else:
        signal = "AVVAKTA"

    confidence = min(95, max(50, 50 + abs(total_score - 50)))
    risk_level = (
        "HÖG"
        if atr_percent >= 4 or (rsi14 is not None and (rsi14 >= 75 or rsi14 <= 25))
        else "MEDEL"
        if atr_percent >= 1.5
        else "LÅG"
    )
    simple = {
        "STARKT KÖP": (
            "Flera indikatorer visar tydlig uppgång. Läget ser positivt ut, "
            "men använd alltid stop-loss."
        ),
        "KÖP": "Marknaden visar mer styrka än svaghet. Ett försiktigt köp kan övervägas.",
        "AVVAKTA": "Signalerna är blandade. Det är klokt att vänta på ett tydligare läge.",
        "SÄLJ": "Marknaden visar svaghet. Överväg att minska eller stänga en befintlig position.",
        "STARKT SÄLJ": (
            "Flera indikatorer visar tydlig nedgång. Risken för fortsatt fall är förhöjd."
        ),
    }[signal]
    return {
        "ema_20": ema20,
        "ema_50": ema50,
        "ema_200": ema200,
        "rsi_14": rsi14,
        "atr_14": atr14,
        "macd": macd_value,
        "macd_signal": macd_signal,
        "macd_histogram": macd_histogram,
        "trend_score": trend_score,
        "momentum_score": momentum_score,
        "volatility_score": volatility_score,
        "total_score": total_score,
        "signal": signal,
        "confidence": confidence,
        "risk_level": risk_level,
        "simple_explanation": simple,
        "warnings": warnings,
        "explanation": explanations,
    }
