from unittest.mock import AsyncMock, patch


class FakeState:
    trading_mode = "off"
    emergency_stop = False
    updated_at = None


@patch("app.api.routes.system.get_or_create_system_state", new_callable=AsyncMock)
def test_system_status(mock_get_state: AsyncMock, api_client) -> None:
    mock_get_state.return_value = FakeState()
    response = api_client.get("/api/v1/system/status")
    assert response.status_code == 200
    assert response.json()["trading_mode"] == "off"
    assert response.json()["live_trading_available"] is False


@patch("app.api.routes.system.get_or_create_system_state", new_callable=AsyncMock)
def test_system_route_is_not_registered_twice(
    mock_get_state: AsyncMock,
    api_client,
) -> None:
    mock_get_state.return_value = FakeState()

    assert api_client.get("/api/v1/system/status").status_code == 200
    assert api_client.get("/api/v1/api/v1/system/status").status_code == 404
