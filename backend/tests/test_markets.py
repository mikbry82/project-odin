from fastapi.testclient import TestClient

from app.main import app
from app.services import market_data

client = TestClient(app)


def test_markets_endpoint(monkeypatch) -> None:
    async def fake_market_overview():
        return market_data.fallback_markets(), True

    monkeypatch.setattr("app.api.routes.markets.get_market_overview", fake_market_overview)
    response = client.get("/api/v1/markets")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["markets"]) == 4
    assert payload["is_fallback"] is True
    assert payload["markets"][0]["symbol"] == "BTCUSDT"
