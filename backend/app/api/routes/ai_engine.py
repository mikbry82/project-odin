from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auto_trader import AutoTraderConfig
from app.models.paper import PaperAccount, PaperPosition
from app.schemas.ai_engine import AIAnalysisResponse
from app.services.ai_engine import PortfolioContext, run_ai_engine
from app.services.market_data import ALLOWED_INTERVALS, SYMBOLS, get_candles

router = APIRouter(prefix="/ai", tags=["ai-engine"])


@router.get("/analysis", response_model=AIAnalysisResponse)
async def ai_analysis(
    symbol: str = Query("BTCUSDT"),
    interval: str = Query("1h"),
    db: AsyncSession = Depends(get_db_session),
):
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        raise HTTPException(status_code=400, detail="Marknaden stöds inte.")
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail="Tidsintervallet stöds inte.")

    candles, fallback = await get_candles(symbol, interval, 240)
    account = await db.get(PaperAccount, 1)
    positions = list((await db.scalars(select(PaperPosition))).all())
    config = await db.get(AutoTraderConfig, 1)

    equity = account.cash_balance if account else 100000.0
    for position in positions:
        if position.symbol == symbol:
            equity += position.quantity * float(candles[-1]["close"])
        else:
            equity += position.quantity * position.entry_price

    context = PortfolioContext(
        equity=equity,
        cash_balance=account.cash_balance if account else 100000.0,
        open_positions=len(positions),
        max_open_positions=config.max_open_positions if config else 3,
        symbol_already_open=any(position.symbol == symbol for position in positions),
    )
    result = run_ai_engine(candles, context)
    return {
        "symbol": symbol,
        "display_symbol": f"{symbol[:-4]}/USDT",
        "interval": interval,
        "price": float(candles[-1]["close"]),
        "source": "demo-fallback" if fallback else "binance-public",
        **result,
        "generated_at": datetime.now(UTC),
    }
