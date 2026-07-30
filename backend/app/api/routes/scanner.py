from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.auto_trader import AutoTraderConfig
from app.models.paper import PaperPosition, PaperTrade
from app.models.system_state import SystemState
from app.schemas.scanner import (
    AutoTraderCycleResponse,
    AutoTraderSettingsResponse,
    AutoTraderSettingsUpdate,
    PerformanceResponse,
    ScannerResponse,
)
from app.services.market_data import ALLOWED_INTERVALS
from app.services.scanner import scan_markets

router = APIRouter(prefix="/scanner", tags=["market-scanner"])


async def get_config(db: AsyncSession) -> AutoTraderConfig:
    config = await db.get(AutoTraderConfig, 1)
    if config is None:
        config = AutoTraderConfig(id=1)
        db.add(config)
        await db.commit()
        await db.refresh(config)
    return config


@router.get("", response_model=ScannerResponse)
async def scanner(interval: str = Query("1h")):
    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail="Tidsintervallet stöds inte.")
    items = await scan_markets(interval)
    return {"interval": interval, "items": items, "updated_at": datetime.now(UTC)}


@router.get("/auto/settings", response_model=AutoTraderSettingsResponse)
async def get_auto_settings(db: AsyncSession = Depends(get_db_session)):
    return await get_config(db)


@router.put("/auto/settings", response_model=AutoTraderSettingsResponse)
async def update_auto_settings(
    payload: AutoTraderSettingsUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    if payload.interval not in ALLOWED_INTERVALS:
        raise HTTPException(status_code=400, detail="Tidsintervallet stöds inte.")
    config = await get_config(db)
    for key, value in payload.model_dump().items():
        setattr(config, key, value)
    await db.commit()
    await db.refresh(config)
    return config


@router.post("/auto/run", response_model=AutoTraderCycleResponse)
async def run_auto_cycle(db: AsyncSession = Depends(get_db_session)):
    config = await get_config(db)
    if not config.enabled:
        raise HTTPException(status_code=400, detail="Automatisk paper trading är inte aktiverad.")

    system = await db.get(SystemState, 1)
    if system is None or system.trading_mode != "paper" or system.emergency_stop:
        raise HTTPException(
            status_code=400,
            detail="Paper trading måste vara aktivt och nödstoppet avstängt.",
        )

    scan = await scan_markets(config.interval)
    prices = {item["symbol"]: item["price"] for item in scan}
    positions = list(
        (await db.scalars(select(PaperPosition).order_by(PaperPosition.opened_at))).all()
    )
    account = await db.get(
        __import__("app.models.paper", fromlist=["PaperAccount"]).PaperAccount, 1
    )
    if account is None:
        from app.models.paper import PaperAccount

        account = PaperAccount(id=1, cash_balance=100000.0, starting_balance=100000.0)
        db.add(account)
        await db.flush()

    opened: list[str] = []
    closed: list[str] = []
    skipped: list[str] = []

    # First protect existing positions with automatic stop-loss and take-profit.
    for position in list(positions):
        current = prices.get(position.symbol, position.entry_price)
        reason = None
        if position.stop_loss is not None and current <= position.stop_loss:
            reason = "Automatisk stop-loss"
        elif position.take_profit is not None and current >= position.take_profit:
            reason = "Automatisk take-profit"
        if reason:
            proceeds = position.quantity * current
            pnl = (current - position.entry_price) * position.quantity
            account.cash_balance += proceeds
            db.add(
                PaperTrade(
                    symbol=position.symbol,
                    side="SELL",
                    quantity=position.quantity,
                    price=current,
                    realized_pnl=pnl,
                    reason=reason,
                )
            )
            await db.delete(position)
            positions.remove(position)
            closed.append(f"{position.symbol}: {reason}")

    open_symbols = {position.symbol for position in positions}
    candidates = [
        item
        for item in scan
        if item["chief_signal"] in {"STARKT KÖP", "KÖP"}
        and item["chief_confidence"] >= config.minimum_confidence
        and item["chief_risk_level"] != "HÖG"
    ]

    for item in candidates:
        if len(positions) >= config.max_open_positions:
            skipped.append("Maximalt antal öppna positioner är uppnått.")
            break
        if item["symbol"] in open_symbols:
            skipped.append(f"{item['symbol']}: position finns redan.")
            continue
        if account.cash_balance < config.amount_usdt:
            skipped.append("Otillräckligt paper-saldo.")
            break

        price = item["price"]
        quantity = config.amount_usdt / price
        position = PaperPosition(
            symbol=item["symbol"],
            quantity=quantity,
            entry_price=price,
            stop_loss=price * (1 - config.stop_loss_percent / 100),
            take_profit=price * (1 + config.take_profit_percent / 100),
        )
        account.cash_balance -= config.amount_usdt
        db.add(position)
        db.add(
            PaperTrade(
                symbol=item["symbol"],
                side="BUY",
                quantity=quantity,
                price=price,
                reason=(
                    f"Chief AI: {item['chief_signal']}, säkerhet {item['chief_confidence']} %, "
                    f"AI Score {item['chief_score']}/100. {item['chief_summary']}"
                ),
            )
        )
        positions.append(position)
        open_symbols.add(item["symbol"])
        opened.append(item["symbol"])

    config.last_run_at = datetime.utcnow()
    await db.commit()
    return {
        "scanned": len(scan),
        "opened": opened,
        "closed": closed,
        "skipped": skipped,
        "message": "Automatisk paper-cykel genomförd.",
        "run_at": datetime.now(UTC),
    }


@router.get("/performance", response_model=PerformanceResponse)
async def performance(db: AsyncSession = Depends(get_db_session)):
    sells = list(
        (
            await db.scalars(
                select(PaperTrade).where(PaperTrade.side == "SELL").order_by(PaperTrade.created_at)
            )
        ).all()
    )
    wins = [trade.realized_pnl for trade in sells if trade.realized_pnl > 0]
    losses = [trade.realized_pnl for trade in sells if trade.realized_pnl < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    count = len(sells)
    return {
        "closed_trades": count,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": (len(wins) / count * 100) if count else 0,
        "total_realized_pnl": sum(trade.realized_pnl for trade in sells),
        "average_win": (gross_profit / len(wins)) if wins else 0,
        "average_loss": (sum(losses) / len(losses)) if losses else 0,
        "profit_factor": (gross_profit / gross_loss) if gross_loss else None,
    }
