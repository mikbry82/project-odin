from app.services.market_data import fallback_candles
from app.strategies.engine import DEFAULT_PARAMETERS, evaluate_strategy, merged_parameters


def test_parameters_merge_with_defaults():
    merged = merged_parameters({"minimum_score": 70})
    assert merged["minimum_score"] == 70
    assert merged["ema_fast"] == DEFAULT_PARAMETERS["ema_fast"]


def test_strategy_is_deterministic():
    candles = fallback_candles("BTCUSDT", 240)
    first = evaluate_strategy(candles)
    second = evaluate_strategy(candles)
    assert first == second
    assert first.signal in {"KÖP", "SÄLJ", "AVVAKTA"}


def test_strategy_handles_incomplete_data():
    result = evaluate_strategy(fallback_candles("BTCUSDT", 20))
    assert result.signal == "AVVAKTA"
    assert result.confidence == 50
