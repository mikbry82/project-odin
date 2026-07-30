from app.schemas.live_trading import RiskSettingsInput
from app.schemas.system import SystemStatusResponse


def test_old_api_values_are_tolerated_and_not_returned() -> None:
    status = SystemStatusResponse.model_validate(
        {
            "trading_mode": "off",
            "operating_mode": "simulation",
            "emergency_stop": False,
            "live_trading_available": False,
            "expert_mode": False,
            "simple_mode": True,
        }
    )

    assert "expert_mode" not in status.model_dump()
    assert "simple_mode" not in status.model_dump()


def test_old_config_value_does_not_change_risk_controls() -> None:
    settings = RiskSettingsInput.model_validate(
        {
            "max_order_eur": 100,
            "max_daily_eur": 300,
            "max_orders_daily": 3,
            "daily_loss_eur": 100,
            "cooldown_seconds": 300,
            "allowed_pairs": ["BTC/EUR", "ETH/EUR"],
            "buy_only": True,
            "risk_warning_accepted": False,
            "expert_mode": False,
        }
    )

    assert settings.risk_warning_accepted is False
    assert settings.buy_only is True
    assert "expert_mode" not in settings.model_dump()
