from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


class FakeState:
    trading_mode = "off"
    emergency_stop = False
    updated_at = None


@patch("app.api.routes.system.get_or_create_system_state", new_callable=AsyncMock)
def test_system_status(mock_get_state: AsyncMock) -> None:
    mock_get_state.return_value = FakeState()
    with TestClient(app) as client:
        response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert response.json()["trading_mode"] == "off"
    assert response.json()["live_trading_available"] is False


def test_system_route_is_not_registered_twice() -> None:
    paths = {route.path for route in app.routes}
    assert "/api/v1/system/status" in paths
    assert "/api/v1/api/v1/system/status" not in paths
