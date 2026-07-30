import json
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.db.session import get_db_session
from app.exchanges.base import Credentials, CredentialStatus
from app.exchanges.errors import ExchangeError
from app.exchanges.kraken import PAIR_CACHE_SECONDS, KrakenProvider
from app.models.live_trading import AssetCostBasis, LiveOrder, PairRiskLimit
from app.models.system_state import TradingMode
from app.schemas.live_trading import (
    AccountFillResponse,
    AccountOrderResponse,
    BalanceResponse,
    CancelAllInput,
    CancelOrderInput,
    ConnectionStatus,
    CredentialInput,
    CredentialStoreStatus,
    LiveAccountResponse,
    LiveModeActivation,
    LiveOrderResponse,
    OrderConfirmationInput,
    OrderPreviewInput,
    OrderPreviewResponse,
    PairDiscoveryResponse,
    RiskSettingsInput,
    RiskSettingsResponse,
    TradingPairResponse,
)
from app.services.credential_store import (
    CredentialStoreError,
    CredentialStoreErrorCategory,
    credential_store,
)
from app.services.live_trading import (
    LiveTradingViolation,
    confirm_order,
    create_preview,
    get_or_create_risk_settings,
    record_transition,
)
from app.services.system_state import get_or_create_system_state

router = APIRouter(prefix="/live", tags=["live-trading"])
provider = KrakenProvider()
LIVE_CONFIRMATION_PHRASE = "JAG FÖRSTÅR RISKEN"

CREDENTIAL_ERROR_MESSAGES = {
    CredentialStoreErrorCategory.UNAVAILABLE: (
        "Windows Autentiseringshanterare kunde inte nås. Kontrollera att programmet "
        "körs under ditt vanliga Windows-konto."
    ),
    CredentialStoreErrorCategory.PACKAGING_SUPPORT_MISSING: (
        "Den installerade backend-tjänsten saknar stöd för Windows "
        "Autentiseringshanterare. Installera om Project Odin."
    ),
    CredentialStoreErrorCategory.ACCESS_DENIED: (
        "Windows nekade åtkomst till Autentiseringshanteraren. Kör Project Odin "
        "under ditt vanliga Windows-konto och försök igen."
    ),
    CredentialStoreErrorCategory.WRITE_FAILED: (
        "Kraken-nyckeln kunde inte skrivas till Windows Autentiseringshanterare. "
        "Testa säker lagring och kontrollera Windows-kontot."
    ),
    CredentialStoreErrorCategory.VERIFICATION_FAILED: (
        "Den sparade testuppgiften kunde inte verifieras. Inga Kraken-nycklar sparades."
    ),
    CredentialStoreErrorCategory.DELETE_FAILED: (
        "Uppgifterna kunde inte tas bort från Windows Autentiseringshanterare. "
        "Öppna Autentiseringshanteraren och kontrollera Project Odin-poster."
    ),
    CredentialStoreErrorCategory.UNSAFE_BACKEND: (
        "En osäker autentiseringsbackend valdes. Project Odin kräver Windows "
        "Autentiseringshanterare."
    ),
}


def credential_error_message(error: CredentialStoreError) -> str:
    return CREDENTIAL_ERROR_MESSAGES[error.category]


def connection_response(validation) -> ConnectionStatus:
    return ConnectionStatus(
        status=validation.status.value,
        account_access=validation.account_access,
        order_access=validation.order_access,
        withdrawal_access_absent=validation.withdrawal_access_absent,
        permission_verification_complete=(
            validation.order_access is not None and validation.withdrawal_access_absent is not None
        ),
        warning=validation.warning,
    )


async def stored_credentials() -> Credentials:
    try:
        credentials = await run_in_threadpool(credential_store.load)
    except CredentialStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=credential_error_message(exc),
        ) from exc
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Anslut Kraken innan live-funktioner används.",
        )
    return credentials


@router.get("/connection", response_model=ConnectionStatus)
async def get_connection() -> ConnectionStatus:
    try:
        credentials = await run_in_threadpool(credential_store.load)
    except CredentialStoreError as exc:
        return ConnectionStatus(
            status=CredentialStatus.UNAVAILABLE.value,
            warning=credential_error_message(exc),
        )
    if credentials is None:
        return ConnectionStatus(status=CredentialStatus.DISCONNECTED.value)
    try:
        return connection_response(await provider.validate_credentials(credentials))
    except ExchangeError as exc:
        return ConnectionStatus(
            status=CredentialStatus.INVALID_PERMISSIONS.value,
            warning=exc.user_message,
        )


@router.post("/credentials", response_model=ConnectionStatus)
async def save_credentials(payload: CredentialInput) -> ConnectionStatus:
    credentials = Credentials(
        api_key=payload.api_key.get_secret_value(),
        api_secret=payload.api_secret.get_secret_value(),
    )
    try:
        validation = await provider.validate_credentials(credentials)
        if validation.status is not CredentialStatus.CONNECTED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Kraken-nyckeln kunde inte valideras.",
            )
        await run_in_threadpool(credential_store.save, credentials)
    except CredentialStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=credential_error_message(exc),
        ) from exc
    except ExchangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.user_message
        ) from exc
    return connection_response(validation)


@router.post("/connection/test", response_model=ConnectionStatus)
async def reconnect_test(
    credentials: Credentials = Depends(stored_credentials),
) -> ConnectionStatus:
    try:
        return connection_response(await provider.validate_credentials(credentials))
    except ExchangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.user_message
        ) from exc


@router.delete("/credentials", response_model=ConnectionStatus)
async def delete_credentials(
    session: AsyncSession = Depends(get_db_session),
) -> ConnectionStatus:
    try:
        await run_in_threadpool(credential_store.delete)
    except CredentialStoreError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=credential_error_message(exc),
        ) from exc
    state = await get_or_create_system_state(session)
    state.trading_mode = TradingMode.OFF.value
    state.emergency_stop = True
    await session.commit()
    return ConnectionStatus(status=CredentialStatus.DISCONNECTED.value)


@router.post("/credential-store/test", response_model=CredentialStoreStatus)
async def test_credential_store(request: Request) -> CredentialStoreStatus:
    client_host = request.client.host if request.client else ""
    if client_host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Säker lagring kan endast testas lokalt.",
        )
    capability = await run_in_threadpool(credential_store.capability, refresh=True)
    if capability.available:
        return CredentialStoreStatus(
            available=True,
            backend=capability.backend_class,
            message=(
                "Windows Autentiseringshanterare fungerar. Den tillfälliga "
                "testuppgiften har tagits bort."
            ),
            temporary_credential_deleted=capability.temporary_credential_deleted,
        )
    category = capability.category or CredentialStoreErrorCategory.UNAVAILABLE
    return CredentialStoreStatus(
        available=False,
        backend=capability.backend_class,
        category=category.value,
        message=CREDENTIAL_ERROR_MESSAGES[category],
        temporary_credential_deleted=capability.temporary_credential_deleted,
    )


@router.get("/pairs", response_model=PairDiscoveryResponse)
async def get_pairs(
    refresh: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> PairDiscoveryResponse:
    pairs = await provider.fetch_pair_metadata(refresh=refresh)
    settings = await get_or_create_risk_settings(session)
    allowed = set(settings.allowed_pairs.split(","))
    eur_pairs = [pair for pair in pairs if pair.quote_symbol == "EUR"]
    return PairDiscoveryResponse(
        pairs=[
            TradingPairResponse(
                **{
                    **pair.__dict__,
                    "minimum_quantity": float(pair.minimum_quantity),
                    "minimum_cost": float(pair.minimum_cost),
                    "allowed": pair.symbol in allowed,
                }
            )
            for pair in eur_pairs
        ],
        cached_for_seconds=PAIR_CACHE_SECONDS,
        updated_at=datetime.now(UTC),
    )


@router.get("/account", response_model=LiveAccountResponse)
async def get_live_account(
    session: AsyncSession = Depends(get_db_session),
    credentials: Credentials = Depends(stored_credentials),
) -> LiveAccountResponse:
    now = datetime.now(UTC)
    balances = [
        item for item in await provider.fetch_normalized_balances(credentials) if item.total
    ]
    pairs = await provider.fetch_pair_metadata()
    direct_pairs = {
        pair.base_symbol: pair for pair in pairs if pair.quote_symbol == "EUR" and pair.tradable
    }
    valued: list[tuple[object, Decimal | None, str]] = []
    for balance in balances:
        if balance.display_symbol == "EUR":
            valued.append((balance, balance.total, "direct"))
            continue
        pair = direct_pairs.get(balance.display_symbol)
        if pair is None:
            valued.append((balance, None, "unpriced"))
            continue
        try:
            value = balance.total * await provider.fetch_current_price(pair.symbol)
            valued.append((balance, value, "direct"))
        except ExchangeError:
            valued.append((balance, None, "unpriced"))
    total = sum((value for _, value, _ in valued if value is not None), Decimal("0"))
    opened, recent = await provider.fetch_account_orders(credentials)
    fills = await provider.fetch_account_fills(credentials)
    cost_result = await session.execute(select(AssetCostBasis))
    cost_bases = {item.canonical_asset_id: item for item in cost_result.scalars()}
    return LiveAccountResponse(
        connection_status="connected",
        last_successful_refresh=now,
        total_estimated_eur=float(total),
        available_eur=float(
            next(
                (item.available for item in balances if item.display_symbol == "EUR"), Decimal("0")
            )
        ),
        balances=[
            BalanceResponse(
                canonical_asset_id=item.canonical_asset_id,
                display_symbol=item.display_symbol,
                total=float(item.total),
                available=float(item.available),
                reserved=float(item.reserved),
                estimated_eur_value=(float(value) if value is not None else None),
                allocation_percent=(
                    float(value / total * 100) if value is not None and total else None
                ),
                pricing_status=status_value,
                price_timestamp=(now if value is not None else None),
                average_acquisition_price_eur=(
                    cost_bases[item.canonical_asset_id].average_acquisition_price_eur
                    if item.canonical_asset_id in cost_bases
                    else None
                ),
                estimated_unrealized_pnl_eur=(
                    float(
                        value
                        - item.total
                        * Decimal(
                            str(cost_bases[item.canonical_asset_id].average_acquisition_price_eur)
                        )
                    )
                    if value is not None
                    and item.canonical_asset_id in cost_bases
                    and cost_bases[item.canonical_asset_id].average_acquisition_price_eur
                    is not None
                    else None
                ),
            )
            for item, value, status_value in valued
        ],
        open_orders=[AccountOrderResponse(**item.__dict__) for item in opened],
        recent_orders=[AccountOrderResponse(**item.__dict__) for item in recent],
        recent_fills=[AccountFillResponse(**item.__dict__) for item in fills],
    )


@router.get("/risk", response_model=RiskSettingsResponse)
async def get_risk(
    session: AsyncSession = Depends(get_db_session),
) -> RiskSettingsResponse:
    settings = await get_or_create_risk_settings(session)
    state = await get_or_create_system_state(session)
    limits = (await session.execute(select(PairRiskLimit))).scalars().all()
    return RiskSettingsResponse(
        max_order_eur=settings.max_order_eur,
        max_daily_eur=settings.max_daily_eur,
        max_orders_daily=settings.max_orders_daily,
        daily_loss_eur=settings.daily_loss_eur,
        cooldown_seconds=settings.cooldown_seconds,
        allowed_pairs=settings.allowed_pairs.split(","),
        pair_limits=[
            {
                "symbol": item.symbol,
                "enabled": item.enabled,
                "max_order_eur": item.max_order_eur,
                "max_daily_eur": item.max_daily_eur,
                "max_orders_daily": item.max_orders_daily,
            }
            for item in limits
        ],
        buy_only=settings.buy_only,
        risk_warning_accepted=settings.risk_warning_accepted,
        kill_switch_active=state.emergency_stop,
    )


@router.put("/risk", response_model=RiskSettingsResponse)
async def update_risk(
    payload: RiskSettingsInput,
    session: AsyncSession = Depends(get_db_session),
) -> RiskSettingsResponse:
    if payload.max_daily_eur < payload.max_order_eur:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dagsgränsen får inte vara lägre än ordergränsen.",
        )
    discovered = await provider.fetch_pair_metadata()
    valid = {pair.symbol for pair in discovered if pair.quote_symbol == "EUR" and pair.tradable}
    if not payload.allowed_pairs or any(symbol not in valid for symbol in payload.allowed_pairs):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tillåtna par måste vara aktiva EUR-spotpar från Kraken.",
        )
    settings = await get_or_create_risk_settings(session)
    for key, value in payload.model_dump(exclude={"allowed_pairs", "pair_limits"}).items():
        setattr(settings, key, value)
    settings.allowed_pairs = ",".join(payload.allowed_pairs)
    for item in payload.pair_limits:
        if item.symbol not in valid:
            raise HTTPException(status_code=422, detail="En pargräns använder ett ogiltigt par.")
        limit = await session.get(PairRiskLimit, item.symbol)
        if limit is None:
            limit = PairRiskLimit(symbol=item.symbol)
            session.add(limit)
        for key, value in item.model_dump(exclude={"symbol"}).items():
            setattr(limit, key, value)
    await session.commit()
    state = await get_or_create_system_state(session)
    return RiskSettingsResponse(**payload.model_dump(), kill_switch_active=state.emergency_stop)


@router.post("/mode/enable")
async def enable_live_mode(
    payload: LiveModeActivation,
    session: AsyncSession = Depends(get_db_session),
    credentials: Credentials = Depends(stored_credentials),
) -> dict[str, str]:
    if payload.confirmation_phrase != LIVE_CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bekräftelsefrasen är fel.",
        )
    settings = await get_or_create_risk_settings(session)
    if not settings.risk_warning_accepted:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Godkänn riskvarningen innan live-läget aktiveras.",
        )
    try:
        validation = await provider.validate_credentials(credentials)
    except ExchangeError as exc:
        raise HTTPException(status_code=400, detail=exc.user_message) from exc
    if validation.status is not CredentialStatus.CONNECTED:
        raise HTTPException(status_code=409, detail="Kraken är inte anslutet.")
    state = await get_or_create_system_state(session)
    if state.emergency_stop:
        raise HTTPException(
            status_code=409,
            detail="Nödstoppet måste återställas separat innan live-läget aktiveras.",
        )
    state.trading_mode = TradingMode.LIVE.value
    await session.commit()
    return {"trading_mode": TradingMode.LIVE.value}


@router.post("/preview", response_model=OrderPreviewResponse)
async def preview(
    payload: OrderPreviewInput,
    session: AsyncSession = Depends(get_db_session),
    credentials: Credentials = Depends(stored_credentials),
) -> OrderPreviewResponse:
    if payload.side == "buy" and (payload.amount_eur is None) == (payload.amount_crypto is None):
        raise HTTPException(
            status_code=422, detail="Ange antingen belopp i EUR eller antal krypto."
        )
    if payload.side == "sell" and (
        payload.amount_eur is not None
        or (payload.amount_crypto is None) == (payload.sell_percentage is None)
    ):
        raise HTTPException(
            status_code=422,
            detail="Ange antal krypto eller procent av tillgängligt saldo.",
        )
    try:
        order = await create_preview(
            session,
            provider,
            credentials,
            symbol=payload.symbol,
            side=payload.side,
            order_type=payload.order_type,
            amount_eur=(Decimal(str(payload.amount_eur)) if payload.amount_eur else None),
            amount_crypto=(Decimal(str(payload.amount_crypto)) if payload.amount_crypto else None),
            sell_percentage=payload.sell_percentage,
            limit_price=(Decimal(str(payload.limit_price)) if payload.limit_price else None),
            recommendation_price=(
                Decimal(str(payload.recommendation_price)) if payload.recommendation_price else None
            ),
            max_slippage_percent=Decimal(str(payload.max_slippage_percent)),
        )
    except (LiveTradingViolation, ExchangeError) as exc:
        detail = exc.user_message if isinstance(exc, ExchangeError) else str(exc)
        raise HTTPException(status_code=409, detail=detail) from exc
    settings = await get_or_create_risk_settings(session)
    pair_limit = await session.get(PairRiskLimit, payload.symbol)
    rules = await provider.fetch_symbol_rules(payload.symbol)
    maximum_order = settings.max_order_eur
    if pair_limit and pair_limit.max_order_eur is not None:
        maximum_order = min(maximum_order, pair_limit.max_order_eur)
    warnings = ["Riktiga pengar kommer att användas."]
    if payload.order_type == "market":
        warnings.append("Marknadsorderns slutpris kan avvika. Beräknad kostnad är inte garanterad.")
    else:
        warnings.append("Limitordern kan förbli öppen och helt eller delvis ofylld.")
    normalized_balances = await provider.fetch_normalized_balances(credentials)
    available_eur = float(
        next(
            (item.available for item in normalized_balances if item.display_symbol == "EUR"),
            Decimal("0"),
        )
    )
    snapshot = json.loads(order.submitted_values or "{}")
    market_price = float(snapshot.get("market_price", order.preview_price))
    available_crypto = (
        float(snapshot.get("available_crypto", 0)) if payload.side == "sell" else None
    )
    fee = order.estimated_fee or 0
    slippage = payload.max_slippage_percent / 100
    pair_risk = await session.get(PairRiskLimit, payload.symbol)
    if payload.recommendation_price:
        movement = abs(order.preview_price - payload.recommendation_price)
        if movement / payload.recommendation_price >= 0.01:
            warnings.append("Priset har ändrats minst 1 % sedan rekommendationen.")
    return OrderPreviewResponse(
        preview_id=order.preview_id,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        requested_amount=order.requested_amount,
        estimated_quantity=order.estimated_quantity,
        current_market_price=market_price,
        limit_price=(order.preview_price if order.order_type == "limit" else None),
        estimated_total=order.estimated_total,
        estimated_fee=order.estimated_fee,
        maximum_order_eur=maximum_order,
        minimum_quantity=float(rules.minimum_quantity),
        minimum_cost=float(rules.minimum_cost),
        quantity_decimals=rules.quantity_decimals,
        price_decimals=rules.price_decimals,
        pair_status=rules.status,
        price_timestamp=datetime.now(UTC),
        available_eur=available_eur,
        available_crypto=available_crypto,
        available_crypto_after=(
            available_crypto - order.estimated_quantity if available_crypto is not None else None
        ),
        sell_percentage=(
            float(payload.sell_percentage)
            if payload.sell_percentage is not None
            else (order.estimated_quantity / available_crypto * 100 if available_crypto else None)
        ),
        estimated_gross_proceeds=(order.estimated_total if payload.side == "sell" else None),
        estimated_net_proceeds=(order.estimated_total - fee if payload.side == "sell" else None),
        max_slippage_percent=payload.max_slippage_percent,
        estimated_price_low=market_price * (1 - slippage),
        estimated_price_high=market_price * (1 + slippage),
        applied_risk_limits={
            "global_max_order_eur": settings.max_order_eur,
            "global_max_daily_eur": settings.max_daily_eur,
            "global_max_orders_daily": settings.max_orders_daily,
            "daily_loss_eur": settings.daily_loss_eur,
            "cooldown_seconds": settings.cooldown_seconds,
            "buy_only": settings.buy_only,
            "pair_max_order_eur": pair_risk.max_order_eur if pair_risk else None,
            "pair_max_daily_eur": pair_risk.max_daily_eur if pair_risk else None,
            "pair_max_orders_daily": pair_risk.max_orders_daily if pair_risk else None,
        },
        warnings=warnings,
        expires_at=order.expires_at,
    )


@router.post("/orders/confirm", response_model=LiveOrderResponse)
async def confirm(
    payload: OrderConfirmationInput,
    session: AsyncSession = Depends(get_db_session),
    credentials: Credentials = Depends(stored_credentials),
) -> LiveOrderResponse:
    preview_result = await session.execute(
        select(LiveOrder).where(LiveOrder.preview_id == payload.preview_id)
    )
    preview_order = preview_result.scalar_one_or_none()
    expected_confirmation = (
        "Bekräfta riktig försäljning"
        if preview_order and preview_order.side == "sell"
        else "Bekräfta riktigt köp"
    )
    if payload.confirmation_text != expected_confirmation:
        raise HTTPException(status_code=409, detail="Bekräftelsetexten matchar inte ordern.")
    try:
        order = await confirm_order(session, provider, credentials, payload.preview_id)
    except LiveTradingViolation as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    messages = {
        "open": "Ordern har skickats till Kraken.",
        "filled": "Ordern är fylld.",
        "unknown_pending_reconciliation": (
            "Orderresultatet är osäkert. Skicka inte en ny order medan Odin kontrollerar status."
        ),
        "failed": "Kraken avvisade ordern.",
    }
    return LiveOrderResponse(
        internal_order_id=order.id,
        status=order.status,
        exchange_order_id=order.exchange_order_id,
        message=messages.get(order.status, "Orderstatusen har uppdaterats."),
        submitted_at=order.user_confirmed_at,
        symbol=order.symbol,
        side=order.side,
        order_type=order.order_type,
        quantity=order.estimated_quantity,
        amount_eur=order.estimated_total,
        submitted_price=(order.preview_price if order.order_type == "limit" else None),
    )


@router.post("/kill-switch")
async def activate_kill_switch(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    state = await get_or_create_system_state(session)
    state.emergency_stop = True
    state.trading_mode = TradingMode.OFF.value
    await session.commit()
    return {"kill_switch_active": True}


@router.post("/orders/cancel-all")
async def cancel_all(
    _: CancelAllInput,
    session: AsyncSession = Depends(get_db_session),
    credentials: Credentials = Depends(stored_credentials),
) -> dict[str, int]:
    result = await session.execute(
        select(LiveOrder).where(
            LiveOrder.status.in_(("open", "partially_filled")),
            LiveOrder.exchange_order_id.is_not(None),
        )
    )
    cancelled = 0
    for order in result.scalars():
        try:
            if await provider.cancel_open_order(credentials, order.exchange_order_id):
                await record_transition(session, order, "cancelled", "user_cancel_all")
                cancelled += 1
        except ExchangeError:
            continue
    await session.commit()
    return {"cancelled": cancelled}


@router.post("/orders/{exchange_order_id}/cancel")
async def cancel_one(
    exchange_order_id: str,
    _: CancelOrderInput,
    credentials: Credentials = Depends(stored_credentials),
) -> dict[str, bool]:
    open_orders, _recent = await provider.fetch_account_orders(credentials)
    if exchange_order_id not in {item.exchange_order_id for item in open_orders}:
        raise HTTPException(status_code=409, detail="Endast en öppen spotorder kan avbrytas.")
    try:
        cancelled = await provider.cancel_open_order(credentials, exchange_order_id)
    except ExchangeError as exc:
        raise HTTPException(status_code=409, detail=exc.user_message) from exc
    if not cancelled:
        raise HTTPException(status_code=409, detail="Kraken bekräftade inte avbrottet.")
    return {"cancelled": True}
