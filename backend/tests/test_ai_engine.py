from app.services.ai_engine import PortfolioContext, run_ai_engine
from app.services.market_data import fallback_candles


def test_ai_engine_returns_six_agents_and_chief():
    result = run_ai_engine(fallback_candles("BTCUSDT", 240))
    assert len(result["agents"]) == 6
    assert result["chief"]["verdict"] in {"STARKT KÖP", "KÖP", "AVVAKTA", "SÄLJ", "STARKT SÄLJ"}
    assert 0 <= result["chief"]["score"] <= 100
    assert 0 <= result["chief"]["position_size_percent"] <= 5


def test_portfolio_gate_blocks_duplicate_position():
    context = PortfolioContext(
        equity=100000,
        cash_balance=80000,
        open_positions=1,
        max_open_positions=3,
        symbol_already_open=True,
    )
    result = run_ai_engine(fallback_candles("BTCUSDT", 240), context)
    portfolio = next(agent for agent in result["agents"] if agent["agent"] == "portfolio")
    assert portfolio["verdict"] == "STOPP"
    assert result["chief"]["verdict"] == "AVVAKTA"


def test_offline_agents_are_honest():
    result = run_ai_engine(fallback_candles("ETHUSDT", 240))
    offline = [agent for agent in result["agents"] if agent["status"] == "OFFLINE"]
    assert {agent["agent"] for agent in offline} == {"news", "macro"}
    assert result["chief"]["confidence"] <= 88
