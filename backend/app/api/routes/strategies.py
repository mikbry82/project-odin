from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.strategy import Strategy
from app.schemas.strategy import (
    StrategyCreate,
    StrategyEvaluation,
    StrategyResponse,
    StrategyUpdate,
)
from app.services.market_data import get_candles
from app.strategies.engine import DEFAULT_PARAMETERS, DEFAULT_RISK_PROFILE, evaluate_strategy

router = APIRouter(prefix="/strategies", tags=["strategies"])


async def ensure_default(db: AsyncSession) -> None:
    existing = await db.scalar(select(Strategy.id).limit(1))
    if existing is None:
        db.add(
            Strategy(
                name="Odin Trend v1",
                description="Standardstrategi med EMA, RSI och MACD.",
                strategy_type="ema_rsi",
                active=True,
                parameters=DEFAULT_PARAMETERS.copy(),
                risk_profile=DEFAULT_RISK_PROFILE.copy(),
            )
        )
        await db.commit()


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(db: AsyncSession = Depends(get_db_session)):
    await ensure_default(db)
    return list(
        (await db.scalars(select(Strategy).order_by(Strategy.active.desc(), Strategy.name))).all()
    )


@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(payload: StrategyCreate, db: AsyncSession = Depends(get_db_session)):
    strategy = Strategy(**payload.model_dump(), active=False, version=1)
    db.add(strategy)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "En strategi med det namnet finns redan.") from exc
    await db.refresh(strategy)
    return strategy


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: int, payload: StrategyUpdate, db: AsyncSession = Depends(get_db_session)
):
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(404, "Strategin hittades inte.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(strategy, key, value)
    strategy.version += 1
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(409, "En strategi med det namnet finns redan.") from exc
    await db.refresh(strategy)
    return strategy


@router.post("/{strategy_id}/activate", response_model=StrategyResponse)
async def activate_strategy(strategy_id: int, db: AsyncSession = Depends(get_db_session)):
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(404, "Strategin hittades inte.")
    if not strategy.enabled:
        raise HTTPException(400, "En inaktiverad strategi kan inte aktiveras.")
    await db.execute(update(Strategy).values(active=False))
    strategy.active = True
    await db.commit()
    await db.refresh(strategy)
    return strategy


@router.post("/{strategy_id}/duplicate", response_model=StrategyResponse, status_code=201)
async def duplicate_strategy(strategy_id: int, db: AsyncSession = Depends(get_db_session)):
    original = await db.get(Strategy, strategy_id)
    if original is None:
        raise HTTPException(404, "Strategin hittades inte.")
    suffix = 2
    name = f"{original.name} kopia"
    while await db.scalar(select(Strategy.id).where(Strategy.name == name)):
        name = f"{original.name} kopia {suffix}"
        suffix += 1
    copy = Strategy(
        name=name,
        description=original.description,
        strategy_type=original.strategy_type,
        enabled=True,
        active=False,
        version=1,
        parameters=dict(original.parameters or {}),
        risk_profile=dict(original.risk_profile or {}),
    )
    db.add(copy)
    await db.commit()
    await db.refresh(copy)
    return copy


@router.get("/{strategy_id}/evaluate", response_model=StrategyEvaluation)
async def evaluate(
    strategy_id: int,
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    db: AsyncSession = Depends(get_db_session),
):
    strategy = await db.get(Strategy, strategy_id)
    if strategy is None:
        raise HTTPException(404, "Strategin hittades inte.")
    candles, _ = await get_candles(symbol.upper(), interval, 240)
    decision = evaluate_strategy(candles, strategy.parameters)
    return StrategyEvaluation(
        strategy_id=strategy.id,
        strategy_name=strategy.name,
        signal=decision.signal,
        score=decision.score,
        confidence=decision.confidence,
        reasons=decision.reasons,
        risk_profile=strategy.risk_profile or {},
    )
