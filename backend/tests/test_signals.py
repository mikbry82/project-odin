from app.services.indicators import analyse


def candles(prices):
    return [
        {"open": p, "high": p * 1.01, "low": p * 0.99, "close": p, "volume": 1000} for p in prices
    ]


def test_signal_has_plain_language_fields():
    result = analyse(candles([100 + i * 0.4 for i in range(240)]))
    assert result["signal"] in {"STARKT KÖP", "KÖP", "AVVAKTA", "SÄLJ", "STARKT SÄLJ"}
    assert 0 <= result["confidence"] <= 100
    assert result["risk_level"] in {"LÅG", "MEDEL", "HÖG"}
    assert result["simple_explanation"]
