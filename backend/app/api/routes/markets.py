from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from app.schemas.market import MarketAnalysisResponse, MarketOverviewResponse
from app.services.indicators import analyse
from app.services.market_data import get_candles, get_market_overview

router = APIRouter(prefix="/markets", tags=["markets"])


@router.get("", response_model=MarketOverviewResponse)
async def market_overview() -> MarketOverviewResponse:
    markets, is_fallback = await get_market_overview()
    return MarketOverviewResponse(
        markets=markets,
        source="demo-fallback" if is_fallback else "binance-public",
        is_fallback=is_fallback,
        updated_at=datetime.now(UTC),
    )


@router.get("/{symbol}/analysis", response_model=MarketAnalysisResponse)
async def market_analysis(
    symbol: str, interval: str = Query(default="1h"), limit: int = Query(default=240, ge=50, le=500)
) -> MarketAnalysisResponse:
    normalized = symbol.upper()
    try:
        candles, is_fallback = await get_candles(normalized, interval, limit)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return MarketAnalysisResponse(
        symbol=normalized,
        display_symbol=f"{normalized[:-4]}/USDT",
        interval=interval,
        candles=candles,
        indicators=analyse(candles),
        source="demo-fallback" if is_fallback else "binance-public",
        is_fallback=is_fallback,
        updated_at=datetime.now(UTC),
    )
