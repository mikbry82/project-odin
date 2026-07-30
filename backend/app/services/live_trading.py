import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.exchanges.base import Credentials, ExchangeProvider, OrderRequest
from app.exchanges.errors import ExchangeError, ExchangeUnavailableError
from app.models.live_trading import LiveOrder, LiveOrderTransition, LiveRiskSettings, PairRiskLimit
from app.models.system_state import SystemState, TradingMode

PREVIEW_TTL_SECONDS = 30
ESTIMATED_FEE_RATE = Decimal("0.004")


class LiveTradingViolation(ValueError):
    pass


async def get_or_create_risk_settings(session: AsyncSession) -> LiveRiskSettings:
    settings = await session.get(LiveRiskSettings, 1)
    if settings is None:
        settings = LiveRiskSettings(id=1)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    return settings


async def record_transition(
    session: AsyncSession, order: LiveOrder, status: str, reason: str | None = None
) -> None:
    order.status = status
    session.add(LiveOrderTransition(live_order_id=order.id, status=status, reason=reason))


def _allowed_pairs(settings: LiveRiskSettings) -> set[str]:
    return {item for item in settings.allowed_pairs.split(",") if item}


async def enforce_risk_limits(
    session: AsyncSession,
    settings: LiveRiskSettings,
    *,
    symbol: str,
    side: str,
    amount_eur: Decimal,
    now: datetime,
) -> None:
    if symbol not in _allowed_pairs(settings):
        raise LiveTradingViolation("Valutan är inte tillåten.")
    if settings.buy_only and side != "buy":
        raise LiveTradingViolation("Säljorder är blockerade när endast köp är tillåtna.")
    if amount_eur > Decimal(str(settings.max_order_eur)):
        raise LiveTradingViolation(
            "Ordern stoppades av din riskgräns: högsta belopp per order överskrids."
        )
    pair_limit = await session.get(PairRiskLimit, symbol)
    if pair_limit and not pair_limit.enabled:
        raise LiveTradingViolation("Handelsparet är inaktiverat.")
    if (
        pair_limit
        and pair_limit.max_order_eur is not None
        and amount_eur > Decimal(str(pair_limit.max_order_eur))
    ):
        raise LiveTradingViolation(
            "Ordern stoppades av din riskgräns: parets högsta belopp per order överskrids."
        )
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    completed_statuses = (
        "confirmed",
        "submitting",
        "open",
        "partially_filled",
        "filled",
        "unknown_pending_reconciliation",
    )
    result = await session.execute(
        select(
            func.count(LiveOrder.id),
            func.coalesce(func.sum(LiveOrder.estimated_total), 0.0),
            func.max(LiveOrder.user_confirmed_at),
        ).where(
            LiveOrder.user_confirmed_at >= start,
            LiveOrder.status.in_(completed_statuses),
        )
    )
    count, total, last_confirmed = result.one()
    if count >= settings.max_orders_daily:
        raise LiveTradingViolation("Dagens högsta antal riktiga ordrar är uppnått.")
    if Decimal(str(total)) + amount_eur > Decimal(str(settings.max_daily_eur)):
        raise LiveTradingViolation("Dagens högsta handelsbelopp skulle överskridas.")
    if pair_limit and (
        pair_limit.max_daily_eur is not None or pair_limit.max_orders_daily is not None
    ):
        pair_result = await session.execute(
            select(
                func.count(LiveOrder.id),
                func.coalesce(func.sum(LiveOrder.estimated_total), 0.0),
            ).where(
                LiveOrder.user_confirmed_at >= start,
                LiveOrder.symbol == symbol,
                LiveOrder.status.in_(completed_statuses),
            )
        )
        pair_count, pair_total = pair_result.one()
        if pair_limit.max_orders_daily is not None and pair_count >= pair_limit.max_orders_daily:
            raise LiveTradingViolation("Parets högsta antal ordrar per dag är uppnått.")
        if pair_limit.max_daily_eur is not None and Decimal(str(pair_total)) + amount_eur > Decimal(
            str(pair_limit.max_daily_eur)
        ):
            raise LiveTradingViolation("Parets högsta handelsbelopp per dag skulle överskridas.")
    if last_confirmed and last_confirmed.tzinfo is None:
        last_confirmed = last_confirmed.replace(tzinfo=UTC)
    if last_confirmed and (now - last_confirmed).total_seconds() < settings.cooldown_seconds:
        raise LiveTradingViolation("Vänta tills säkerhetspausen mellan ordrar är slut.")
    loss_result = await session.execute(
        select(func.coalesce(func.sum(LiveOrder.realized_pnl_eur), 0.0)).where(
            LiveOrder.created_at >= start,
            LiveOrder.realized_pnl_eur < 0,
        )
    )
    realized_loss = abs(Decimal(str(loss_result.scalar_one())))
    if realized_loss >= Decimal(str(settings.daily_loss_eur)):
        raise LiveTradingViolation("Den dagliga förlustgränsen är uppnådd.")


async def create_preview(
    session: AsyncSession,
    provider: ExchangeProvider,
    credentials: Credentials,
    *,
    symbol: str,
    side: str,
    order_type: str,
    amount_eur: Decimal | None,
    amount_crypto: Decimal | None = None,
    limit_price: Decimal | None = None,
    recommendation_price: Decimal | None = None,
    max_slippage_percent: Decimal = Decimal("1"),
) -> LiveOrder:
    state = await session.get(SystemState, 1)
    if state is None or state.trading_mode != TradingMode.LIVE.value:
        raise LiveTradingViolation("Livehandel är inte aktiverad.")
    if state.emergency_stop:
        raise LiveTradingViolation("Nödstoppet är aktiverat.")
    now = datetime.now(UTC)
    settings = await get_or_create_risk_settings(session)
    pair_limit = await session.get(PairRiskLimit, symbol)
    rules = await provider.fetch_symbol_rules(symbol)
    if rules.status != "online":
        raise LiveTradingViolation("Handelsparet är inte tillgängligt för handel.")
    market_price = await provider.fetch_current_price(symbol)
    price = limit_price if order_type == "limit" else market_price
    if order_type == "limit" and price is None:
        raise LiveTradingViolation("En limitorder kräver ett pris.")
    if order_type == "limit" and price.as_tuple().exponent < -rules.price_decimals:
        raise LiveTradingViolation(
            "Limitpriset har för många decimaler. Justera priset och skapa en ny förhandsvisning."
        )
    if (amount_eur is None) == (amount_crypto is None):
        raise LiveTradingViolation("Ange antingen belopp i EUR eller antal krypto.")
    if amount_crypto is not None:
        if amount_crypto.as_tuple().exponent < -rules.quantity_decimals:
            raise LiveTradingViolation("Kryptomängden har för många decimaler.")
        quantity = amount_crypto
        amount_eur = quantity * price
    else:
        quantity = (amount_eur / price).quantize(
            Decimal(1).scaleb(-rules.quantity_decimals), rounding=ROUND_DOWN
        )
    total = quantity * price
    await enforce_risk_limits(
        session, settings, symbol=symbol, side=side, amount_eur=total, now=now
    )
    if quantity < rules.minimum_quantity or total < rules.minimum_cost:
        raise LiveTradingViolation("Beloppet understiger Krakens minimigräns.")
    balances = await provider.fetch_balances(credentials)
    required_asset = rules.quote_asset if side == "buy" else rules.base_asset
    required = total if side == "buy" else quantity
    balance = balances.get(required_asset, Decimal("0"))
    if balance < required:
        raise LiveTradingViolation("Otillräckligt EUR-saldo.")
    warnings = ["Riktiga pengar kommer att användas."]
    if recommendation_price:
        movement = abs(market_price - recommendation_price) / recommendation_price
        if movement >= Decimal("0.01"):
            warnings.append("Priset har ändrats minst 1 % sedan rekommendationen.")
    preview_id = uuid.uuid4().hex[:20]
    client_order_id = uuid.uuid4().hex[:18]
    await provider.preview_order(
        credentials,
        OrderRequest(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price if order_type == "limit" else None,
            client_order_id=client_order_id,
        ),
    )
    order = LiveOrder(
        id=str(uuid.uuid4()),
        preview_id=preview_id,
        client_order_id=client_order_id,
        symbol=symbol,
        side=side,
        order_type=order_type,
        requested_amount=float(amount_eur),
        estimated_quantity=float(quantity),
        preview_price=float(price),
        estimated_total=float(total),
        estimated_fee=float(total * ESTIMATED_FEE_RATE),
        status="previewed",
        expires_at=now + timedelta(seconds=PREVIEW_TTL_SECONDS),
        submitted_values=json.dumps(
            {
                "max_slippage_percent": str(max_slippage_percent),
                "market_price": str(market_price),
                "risk": {
                    "max_order_eur": settings.max_order_eur,
                    "max_daily_eur": settings.max_daily_eur,
                    "max_orders_daily": settings.max_orders_daily,
                    "daily_loss_eur": settings.daily_loss_eur,
                    "cooldown_seconds": settings.cooldown_seconds,
                    "allowed_pairs": settings.allowed_pairs,
                    "buy_only": settings.buy_only,
                    "pair": {
                        "enabled": pair_limit.enabled if pair_limit else None,
                        "max_order_eur": pair_limit.max_order_eur if pair_limit else None,
                        "max_daily_eur": pair_limit.max_daily_eur if pair_limit else None,
                        "max_orders_daily": pair_limit.max_orders_daily if pair_limit else None,
                    },
                },
            },
            sort_keys=True,
        ),
    )
    session.add(order)
    await session.flush()
    await record_transition(session, order, "previewed")
    await session.commit()
    return order


async def confirm_order(
    session: AsyncSession,
    provider: ExchangeProvider,
    credentials: Credentials,
    preview_id: str,
) -> LiveOrder:
    result = await session.execute(select(LiveOrder).where(LiveOrder.preview_id == preview_id))
    order = result.scalar_one_or_none()
    if order is None:
        raise LiveTradingViolation("Förhandsvisningen finns inte.")
    now = datetime.now(UTC)
    expires_at = order.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        if order.status == "previewed":
            await record_transition(session, order, "rejected", "expired_preview")
            await session.commit()
        raise LiveTradingViolation("Orderförhandsvisningen har gått ut. Skapa en ny.")
    if order.status != "previewed":
        raise LiveTradingViolation("Förhandsvisningen har redan använts.")
    state = await session.get(SystemState, 1)
    settings = await get_or_create_risk_settings(session)
    if state is None or state.trading_mode != TradingMode.LIVE.value:
        raise LiveTradingViolation("Livehandel är inte aktiverad.")
    if state.emergency_stop:
        raise LiveTradingViolation("Nödstoppet är aktiverat.")
    snapshot = json.loads(order.submitted_values or "{}")
    pair_limit = await session.get(PairRiskLimit, order.symbol)
    current_risk = {
        "max_order_eur": settings.max_order_eur,
        "max_daily_eur": settings.max_daily_eur,
        "max_orders_daily": settings.max_orders_daily,
        "daily_loss_eur": settings.daily_loss_eur,
        "cooldown_seconds": settings.cooldown_seconds,
        "allowed_pairs": settings.allowed_pairs,
        "buy_only": settings.buy_only,
        "pair": {
            "enabled": pair_limit.enabled if pair_limit else None,
            "max_order_eur": pair_limit.max_order_eur if pair_limit else None,
            "max_daily_eur": pair_limit.max_daily_eur if pair_limit else None,
            "max_orders_daily": pair_limit.max_orders_daily if pair_limit else None,
        },
    }
    if snapshot.get("risk") != current_risk:
        raise LiveTradingViolation("Riskinställningarna har ändrats. Skapa en ny förhandsvisning.")
    current_price = await provider.fetch_current_price(order.symbol)
    slippage = Decimal(snapshot.get("max_slippage_percent", "1")) / 100
    preview_price = Decimal(snapshot.get("market_price", str(order.preview_price)))
    if abs(current_price - preview_price) / preview_price > slippage:
        raise LiveTradingViolation("Prisinformationen är för gammal. Skapa en ny förhandsvisning.")
    await enforce_risk_limits(
        session,
        settings,
        symbol=order.symbol,
        side=order.side,
        amount_eur=Decimal(str(order.estimated_total)),
        now=now,
    )
    claimed = await session.execute(
        update(LiveOrder)
        .where(
            LiveOrder.id == order.id,
            LiveOrder.status == "previewed",
        )
        .values(status="confirmed", user_confirmed_at=now)
    )
    if claimed.rowcount != 1:
        await session.rollback()
        raise LiveTradingViolation("Förhandsvisningen har redan använts.")
    order.user_confirmed_at = now
    order.status = "confirmed"
    session.add(LiveOrderTransition(live_order_id=order.id, status="confirmed"))
    await record_transition(session, order, "submitting")
    order.submitted_values = json.dumps(
        {
            "symbol": order.symbol,
            "side": order.side,
            "order_type": order.order_type,
            "quantity": order.estimated_quantity,
        },
        separators=(",", ":"),
    )
    await session.commit()
    request = OrderRequest(
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=Decimal(str(order.estimated_quantity)),
        price=(Decimal(str(order.preview_price)) if order.order_type == "limit" else None),
        client_order_id=order.client_order_id,
    )
    try:
        exchange_order = await provider.place_spot_order(credentials, request)
    except ExchangeUnavailableError:
        await record_transition(
            session, order, "unknown_pending_reconciliation", "exchange_timeout"
        )
        state.emergency_stop = True
        state.trading_mode = TradingMode.OFF.value
        await session.commit()
        return order
    except ExchangeError as exc:
        order.failure_reason = type(exc).__name__
        await record_transition(session, order, "failed", type(exc).__name__)
        await session.commit()
        return order
    order.exchange_order_id = exchange_order.exchange_order_id
    order.exchange_response_status = exchange_order.raw_status
    await record_transition(session, order, exchange_order.status)
    await session.commit()
    return order


async def reconcile_order(
    session: AsyncSession,
    provider: ExchangeProvider,
    credentials: Credentials,
    order: LiveOrder,
) -> LiveOrder:
    if order.status != "unknown_pending_reconciliation":
        return order
    if not order.exchange_order_id:
        discovered = await provider.find_order_by_client_id(credentials, order.client_order_id)
        if discovered is None:
            order.failure_reason = "manual_reconciliation_required"
            await session.commit()
            return order
        order.exchange_order_id = discovered.exchange_order_id
        order.exchange_response_status = discovered.raw_status
        await record_transition(session, order, discovered.status)
        await session.commit()
        return order
    exchange_order = await provider.fetch_order_status(credentials, order.exchange_order_id)
    order.exchange_response_status = exchange_order.raw_status
    await record_transition(session, order, exchange_order.status)
    await session.commit()
    return order
