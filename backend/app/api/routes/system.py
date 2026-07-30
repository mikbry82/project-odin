from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.system_state import TradingMode
from app.schemas.system import SystemStatusResponse, TradingModeUpdate
from app.services.system_state import get_or_create_system_state

router = APIRouter(prefix="/system", tags=["system"])


def to_response(state) -> SystemStatusResponse:
    return SystemStatusResponse(
        trading_mode=TradingMode(state.trading_mode),
        operating_mode=(
            "live_confirmation" if state.trading_mode == TradingMode.LIVE.value else "simulation"
        ),
        emergency_stop=state.emergency_stop,
        live_trading_available=False,
        updated_at=state.updated_at,
    )


@router.get("/status", response_model=SystemStatusResponse)
async def get_status(
    session: AsyncSession = Depends(get_db_session),
) -> SystemStatusResponse:
    state = await get_or_create_system_state(session)
    return to_response(state)


@router.put("/mode", response_model=SystemStatusResponse)
async def update_mode(
    payload: TradingModeUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> SystemStatusResponse:
    state = await get_or_create_system_state(session)

    if payload.trading_mode is TradingMode.LIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Live trading is locked until exchange, risk and audit modules are complete.",
        )
    if state.emergency_stop and payload.trading_mode is not TradingMode.OFF:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reset the emergency stop before enabling trading.",
        )

    state.trading_mode = payload.trading_mode.value
    await session.commit()
    await session.refresh(state)
    return to_response(state)


@router.post("/emergency-stop", response_model=SystemStatusResponse)
async def emergency_stop(
    session: AsyncSession = Depends(get_db_session),
) -> SystemStatusResponse:
    state = await get_or_create_system_state(session)
    state.emergency_stop = True
    state.trading_mode = TradingMode.OFF.value
    await session.commit()
    await session.refresh(state)
    return to_response(state)


@router.post("/reset-emergency-stop", response_model=SystemStatusResponse)
async def reset_emergency_stop(
    session: AsyncSession = Depends(get_db_session),
) -> SystemStatusResponse:
    state = await get_or_create_system_state(session)
    state.emergency_stop = False
    state.trading_mode = TradingMode.OFF.value
    await session.commit()
    await session.refresh(state)
    return to_response(state)
