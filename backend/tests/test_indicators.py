from app.services.indicators import analyse, ema, rsi


def test_ema_requires_enough_values():
    assert ema([1.0, 2.0], 3) is None


def test_rsi_for_rising_market_is_high():
    assert (rsi([float(value) for value in range(1, 40)]) or 0) > 70


def test_analysis_returns_bounded_score():
    candles = [
        {"open": value, "high": value + 1, "low": value - 1, "close": value, "volume": 1000}
        for value in range(1, 241)
    ]
    result = analyse(candles)
    assert 0 <= result["total_score"] <= 100
    assert result["signal"] in {"KÖPBEVAKNING", "AVVAKTA", "SVAG"}
