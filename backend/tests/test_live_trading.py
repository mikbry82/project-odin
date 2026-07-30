from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.exchanges.base import (
    Credentials,
    CredentialStatus,
    CredentialValidation,
    ExchangeOrder,
    ExchangeProvider,
    SymbolRules,
)
from app.exchanges.errors import ExchangeUnavailableError
from app.models.live_trading import LiveOrder, LiveRiskSettings, PairRiskLimit
from app.models.system_state import SystemState
from app.services.credential_store import CredentialStore
from app.services.live_trading import (
    LiveTradingViolation,
    confirm_order,
    create_preview,
    enforce_risk_limits,
    reconcile_order,
)


class FakeProvider(ExchangeProvider):
    name = "fake-kraken"

    def __init__(self) -> None:
        self.place_calls = 0
        self.place_result = ExchangeOrder("KRAKEN-1", "open", "submitted")
        self.place_error: Exception | None = None
        self.status_result = ExchangeOrder("KRAKEN-1", "filled", "closed")
        self.discovery_result: ExchangeOrder | None = None
        self.balance = {"EUR": Decimal("1000"), "BTC": Decimal("1")}
        self.validation = CredentialValidation(
            CredentialStatus.CONNECTED, True, None, None, "incomplete"
        )
        self.price_error: Exception | None = None

    async def validate_credentials(self, credentials):
        return self.validation

    async def fetch_balances(self, credentials):
        return self.balance

    async def fetch_trading_pairs(self):
        return ["BTC/EUR", "ETH/EUR"]

    async def fetch_symbol_rules(self, symbol):
        return SymbolRules(symbol, symbol[:3], "EUR", Decimal("0.0001"), Decimal("5"), 2, 8)

    async def fetch_current_price(self, symbol):
        if self.price_error:
            raise self.price_error
        return Decimal("50000")

    async def preview_order(self, credentials, order):
        return Decimal("1")

    async def place_spot_order(self, credentials, order):
        self.place_calls += 1
        if self.place_error:
            raise self.place_error
        return self.place_result

    async def fetch_order_status(self, credentials, exchange_order_id):
        return self.status_result

    async def find_order_by_client_id(self, credentials, client_order_id):
        return self.discovery_result

    async def cancel_open_order(self, credentials, exchange_order_id):
        return True

    async def fetch_recent_fills(self, credentials):
        return []


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as value:
        value.add(SystemState(id=1, trading_mode="live", emergency_stop=False))
        value.add(
            LiveRiskSettings(
                id=1,
                max_order_eur=10,
                max_daily_eur=30,
                max_orders_daily=3,
                daily_loss_eur=10,
                cooldown_seconds=60,
                allowed_pairs="BTC/EUR,ETH/EUR",
                buy_only=True,
                risk_warning_accepted=True,
            )
        )
        await value.commit()
        yield value
    await engine.dispose()


def credentials() -> Credentials:
    return Credentials("not-a-real-key", "not-a-real-secret")


async def make_preview(session: AsyncSession, provider: FakeProvider, **overrides) -> LiveOrder:
    values = {
        "symbol": "BTC/EUR",
        "side": "buy",
        "order_type": "market",
        "amount_eur": Decimal("10"),
        "limit_price": None,
        "recommendation_price": Decimal("50000"),
    }
    values.update(overrides)
    return await create_preview(session, provider, credentials(), **values)


@pytest.mark.asyncio
async def test_credential_validation_reports_incomplete_permissions() -> None:
    result = await FakeProvider().validate_credentials(credentials())
    assert result.status is CredentialStatus.CONNECTED
    assert result.account_access is True
    assert result.order_access is None
    assert result.withdrawal_access_absent is None


@pytest.mark.asyncio
async def test_missing_permissions_are_reported() -> None:
    provider = FakeProvider()
    provider.validation = CredentialValidation(
        CredentialStatus.INVALID_PERMISSIONS, True, False, None, "missing"
    )
    result = await provider.validate_credentials(credentials())
    assert result.status is CredentialStatus.INVALID_PERMISSIONS
    assert result.order_access is False


@pytest.mark.asyncio
async def test_order_preview_is_persisted(session: AsyncSession) -> None:
    order = await make_preview(session, FakeProvider())
    assert order.status == "previewed"
    assert order.estimated_total <= 10
    expires_at = order.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    assert expires_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_minimum_order_validation(session: AsyncSession) -> None:
    with pytest.raises(LiveTradingViolation, match="minimigräns"):
        await make_preview(session, FakeProvider(), amount_eur=Decimal("1"))


@pytest.mark.asyncio
async def test_insufficient_balance(session: AsyncSession) -> None:
    provider = FakeProvider()
    provider.balance["EUR"] = Decimal("0")
    with pytest.raises(LiveTradingViolation, match="saldo"):
        await make_preview(session, provider)


@pytest.mark.asyncio
async def test_crypto_quantity_and_limit_buy_preview(session: AsyncSession) -> None:
    order = await make_preview(
        session,
        FakeProvider(),
        order_type="limit",
        amount_eur=None,
        amount_crypto=Decimal("0.0002"),
        limit_price=Decimal("49000"),
    )
    assert order.estimated_quantity == pytest.approx(0.0002)
    assert order.preview_price == pytest.approx(49000)
    assert order.estimated_total == pytest.approx(9.8)


@pytest.mark.asyncio
async def test_invalid_limit_price_precision_is_not_rounded(session: AsyncSession) -> None:
    with pytest.raises(LiveTradingViolation, match="för många decimaler"):
        await make_preview(
            session,
            FakeProvider(),
            order_type="limit",
            limit_price=Decimal("50000.001"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("change", "kwargs", "message"),
    [
        ({"max_order_eur": 5}, {}, "per order"),
        ({"allowed_pairs": "ETH/EUR"}, {}, "inte tillåten"),
        ({"buy_only": True}, {"side": "sell"}, "Säljorder"),
    ],
)
async def test_static_risk_limits(
    session: AsyncSession, change: dict, kwargs: dict, message: str
) -> None:
    settings = await session.get(LiveRiskSettings, 1)
    for key, value in change.items():
        setattr(settings, key, value)
    await session.commit()
    with pytest.raises(LiveTradingViolation, match=message):
        await enforce_risk_limits(
            session,
            settings,
            symbol=kwargs.get("symbol", "BTC/EUR"),
            side=kwargs.get("side", "buy"),
            amount_eur=Decimal("10"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_most_restrictive_per_pair_limit_wins(session: AsyncSession) -> None:
    session.add(
        PairRiskLimit(
            symbol="BTC/EUR",
            enabled=True,
            max_order_eur=5,
            max_daily_eur=8,
            max_orders_daily=1,
        )
    )
    await session.commit()
    settings = await session.get(LiveRiskSettings, 1)
    with pytest.raises(LiveTradingViolation, match="parets högsta belopp per order"):
        await enforce_risk_limits(
            session,
            settings,
            symbol="BTC/EUR",
            side="buy",
            amount_eur=Decimal("6"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_disabled_pair_is_rejected(session: AsyncSession) -> None:
    session.add(PairRiskLimit(symbol="BTC/EUR", enabled=False))
    await session.commit()
    settings = await session.get(LiveRiskSettings, 1)
    with pytest.raises(LiveTradingViolation, match="inaktiverat"):
        await enforce_risk_limits(
            session,
            settings,
            symbol="BTC/EUR",
            side="buy",
            amount_eur=Decimal("5"),
            now=datetime.now(UTC),
        )


async def add_confirmed_order(
    session: AsyncSession,
    *,
    total: float = 10,
    confirmed_at: datetime | None = None,
    pnl: float | None = None,
) -> None:
    now = confirmed_at or datetime.now(UTC)
    session.add(
        LiveOrder(
            id=str(total) + str(now.timestamp()),
            preview_id=str(total) + "p" + str(now.timestamp()),
            client_order_id=str(total) + "c" + str(now.timestamp()),
            symbol="BTC/EUR",
            side="buy",
            order_type="market",
            requested_amount=total,
            estimated_quantity=0.001,
            preview_price=50000,
            estimated_total=total,
            estimated_fee=0.04,
            realized_pnl_eur=pnl,
            status="filled",
            user_confirmed_at=now,
            expires_at=now + timedelta(seconds=30),
            created_at=now,
        )
    )
    await session.commit()


@pytest.mark.asyncio
async def test_daily_total_limit(session: AsyncSession) -> None:
    await add_confirmed_order(
        session,
        total=25,
        confirmed_at=datetime.now(UTC) - timedelta(minutes=2),
    )
    settings = await session.get(LiveRiskSettings, 1)
    with pytest.raises(LiveTradingViolation, match="handelsbelopp"):
        await enforce_risk_limits(
            session,
            settings,
            symbol="BTC/EUR",
            side="buy",
            amount_eur=Decimal("10"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_daily_order_count_limit(session: AsyncSession) -> None:
    for minutes in (5, 4, 3):
        await add_confirmed_order(
            session, confirmed_at=datetime.now(UTC) - timedelta(minutes=minutes)
        )
    settings = await session.get(LiveRiskSettings, 1)
    with pytest.raises(LiveTradingViolation, match="antal"):
        await enforce_risk_limits(
            session,
            settings,
            symbol="BTC/EUR",
            side="buy",
            amount_eur=Decimal("1"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_cooldown_limit(session: AsyncSession) -> None:
    await add_confirmed_order(session, confirmed_at=datetime.now(UTC))
    settings = await session.get(LiveRiskSettings, 1)
    with pytest.raises(LiveTradingViolation, match="säkerhetspausen"):
        await enforce_risk_limits(
            session,
            settings,
            symbol="BTC/EUR",
            side="buy",
            amount_eur=Decimal("1"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_daily_loss_limit(session: AsyncSession) -> None:
    await add_confirmed_order(
        session, confirmed_at=datetime.now(UTC) - timedelta(minutes=2), pnl=-10
    )
    settings = await session.get(LiveRiskSettings, 1)
    with pytest.raises(LiveTradingViolation, match="förlustgränsen"):
        await enforce_risk_limits(
            session,
            settings,
            symbol="BTC/EUR",
            side="buy",
            amount_eur=Decimal("1"),
            now=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_expired_preview_is_rejected(session: AsyncSession) -> None:
    order = await make_preview(session, FakeProvider())
    order.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await session.commit()
    with pytest.raises(LiveTradingViolation, match="gått ut"):
        await confirm_order(session, FakeProvider(), credentials(), order.preview_id)


@pytest.mark.asyncio
async def test_changed_risk_settings_invalidate_preview(session: AsyncSession) -> None:
    provider = FakeProvider()
    order = await make_preview(session, provider)
    settings = await session.get(LiveRiskSettings, 1)
    settings.max_order_eur = 9
    await session.commit()
    with pytest.raises(LiveTradingViolation, match="Riskinställningarna har ändrats"):
        await confirm_order(session, provider, credentials(), order.preview_id)


@pytest.mark.asyncio
async def test_changed_pair_risk_settings_invalidate_preview(session: AsyncSession) -> None:
    provider = FakeProvider()
    session.add(PairRiskLimit(symbol="BTC/EUR", enabled=True, max_order_eur=10))
    await session.commit()
    order = await make_preview(session, provider)
    pair_limit = await session.get(PairRiskLimit, "BTC/EUR")
    pair_limit.max_order_eur = 9
    await session.commit()
    with pytest.raises(LiveTradingViolation, match="Riskinställningarna har ändrats"):
        await confirm_order(session, provider, credentials(), order.preview_id)


@pytest.mark.asyncio
async def test_stale_market_price_invalidates_preview(session: AsyncSession) -> None:
    provider = FakeProvider()
    order = await make_preview(session, provider)
    original = provider.fetch_current_price

    async def changed_price(symbol):
        return (await original(symbol)) * Decimal("1.02")

    provider.fetch_current_price = changed_price
    with pytest.raises(LiveTradingViolation, match="för gammal"):
        await confirm_order(session, provider, credentials(), order.preview_id)


@pytest.mark.asyncio
async def test_duplicate_confirmation_and_double_click_are_blocked(
    session: AsyncSession,
) -> None:
    provider = FakeProvider()
    order = await make_preview(session, provider)
    first = await confirm_order(session, provider, credentials(), order.preview_id)
    assert first.status == "open"
    with pytest.raises(LiveTradingViolation, match="redan använts"):
        await confirm_order(session, provider, credentials(), order.preview_id)
    assert provider.place_calls == 1


@pytest.mark.asyncio
async def test_timeout_before_submission_creates_no_preview(
    session: AsyncSession,
) -> None:
    provider = FakeProvider()
    provider.price_error = ExchangeUnavailableError()
    with pytest.raises(ExchangeUnavailableError):
        await make_preview(session, provider)
    result = await session.execute(select(LiveOrder))
    assert result.scalars().all() == []
    assert provider.place_calls == 0


@pytest.mark.asyncio
async def test_timeout_after_possible_submission_requires_reconciliation(
    session: AsyncSession,
) -> None:
    provider = FakeProvider()
    provider.place_error = ExchangeUnavailableError()
    order = await make_preview(session, provider)
    result = await confirm_order(session, provider, credentials(), order.preview_id)
    assert result.status == "unknown_pending_reconciliation"
    assert provider.place_calls == 1
    state = await session.get(SystemState, 1)
    assert state.emergency_stop is True
    assert state.trading_mode == "off"


@pytest.mark.asyncio
async def test_reconciliation_never_resubmits(session: AsyncSession) -> None:
    provider = FakeProvider()
    provider.place_error = ExchangeUnavailableError()
    provider.discovery_result = ExchangeOrder("KRAKEN-1", "open", "open")
    order = await make_preview(session, provider)
    order = await confirm_order(session, provider, credentials(), order.preview_id)
    reconciled = await reconcile_order(session, provider, credentials(), order)
    assert reconciled.status == "open"
    assert reconciled.exchange_order_id == "KRAKEN-1"
    assert provider.place_calls == 1


@pytest.mark.asyncio
async def test_partial_fill_and_rejected_order_states(session: AsyncSession) -> None:
    provider = FakeProvider()
    provider.place_result = ExchangeOrder("KRAKEN-1", "partially_filled", "open")
    partial = await confirm_order(
        session, provider, credentials(), (await make_preview(session, provider)).preview_id
    )
    assert partial.status == "partially_filled"


@pytest.mark.asyncio
async def test_rejected_order_state(session: AsyncSession) -> None:
    provider = FakeProvider()
    provider.place_result = ExchangeOrder(None, "rejected", "rejected")
    rejected = await confirm_order(
        session,
        provider,
        credentials(),
        (await make_preview(session, provider)).preview_id,
    )
    assert rejected.status == "rejected"


@pytest.mark.asyncio
async def test_kill_switch_blocks_preview(session: AsyncSession) -> None:
    state = await session.get(SystemState, 1)
    state.emergency_stop = True
    await session.commit()
    with pytest.raises(LiveTradingViolation, match="Nödstoppet"):
        await make_preview(session, FakeProvider())


def test_credential_deletion(monkeypatch) -> None:
    values = {}

    class FakeKeyring:
        class errors:
            class PasswordDeleteError(Exception):
                pass

        @staticmethod
        def set_password(service, account, value):
            values[(service, account)] = value

        @staticmethod
        def get_password(service, account):
            return values.get((service, account))

        @staticmethod
        def delete_password(service, account):
            if (service, account) not in values:
                raise FakeKeyring.errors.PasswordDeleteError
            del values[(service, account)]

    store = CredentialStore()
    monkeypatch.setattr(store, "_keyring", lambda: FakeKeyring)
    monkeypatch.setattr(store, "_require_available", lambda: None)
    store.save(credentials())
    assert store.load() == credentials()
    store.delete()
    assert store.load() is None


@pytest.mark.asyncio
async def test_kill_switch_persists_across_session_restart(
    session: AsyncSession,
) -> None:
    state = await session.get(SystemState, 1)
    state.emergency_stop = True
    await session.commit()
    session.expire_all()
    reloaded = await session.get(SystemState, 1)
    assert reloaded.emergency_stop is True
