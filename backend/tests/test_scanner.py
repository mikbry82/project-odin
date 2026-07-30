from app.services.indicators import analyse
from app.services.market_data import fallback_candles


def test_scanner_analysis_has_beginner_signal():
    result = analyse(fallback_candles("BTCUSDT", 240))
    assert result["signal"] in {"STARKT KÖP", "KÖP", "AVVAKTA", "SÄLJ", "STARKT SÄLJ"}
    assert 0 <= result["total_score"] <= 100
    assert 50 <= result["confidence"] <= 95
