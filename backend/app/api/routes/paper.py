from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.paper import PaperAccount, PaperPosition, PaperTrade
from app.schemas.paper import PaperOrderCreate, PaperPortfolioResponse
from app.services.market_data import get_market_overview

router = APIRouter(prefix="/paper", tags=["paper-trading"])


async def prices() -> dict[str, float]:
    markets, _ = await get_market_overview()
    return {market["symbol"]: float(market["price"]) for market in markets}


async def account(db: AsyncSession) -> PaperAccount:
    paper_account = await db.get(PaperAccount, 1)
    if paper_account is None:
        paper_account = PaperAccount(
            id=1,
            cash_balance=100000.0,
            starting_balance=100000.0,
        )
        db.add(paper_account)
        await db.commit()
        await db.refresh(paper_account)
    return paper_account


def serialize_position(position: PaperPosition, current_price: float) -> dict[str, Any]:
    market_value = position.quantity * current_price
    unrealized_pnl = (current_price - position.entry_price) * position.quantity
    return {
        "id": position.id,
        "symbol": position.symbol,
        "quantity": position.quantity,
        "entry_price": position.entry_price,
        "current_price": current_price,
        "market_value": market_value,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_percent": ((current_price / position.entry_price) - 1) * 100,
        "stop_loss": position.stop_loss,
        "take_profit": position.take_profit,
        "opened_at": position.opened_at,
    }


def serialize_trade(trade: PaperTrade) -> dict[str, Any]:
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "quantity": trade.quantity,
        "price": trade.price,
        "realized_pnl": trade.realized_pnl,
        "reason": trade.reason,
        "created_at": trade.created_at,
    }


async def portfolio(db: AsyncSession) -> dict[str, Any]:
    paper_account = await account(db)
    current_prices = await prices()
    positions = (
        await db.scalars(select(PaperPosition).order_by(PaperPosition.opened_at.desc()))
    ).all()
    trades = (
        await db.scalars(select(PaperTrade).order_by(PaperTrade.created_at.desc()).limit(30))
    ).all()

    serialized_positions = [
        serialize_position(
            position,
            current_prices.get(position.symbol, position.entry_price),
        )
        for position in positions
    ]
    positions_value = sum(position["market_value"] for position in serialized_positions)
    equity = paper_account.cash_balance + positions_value
    return {
        "starting_balance": paper_account.starting_balance,
        "cash_balance": paper_account.cash_balance,
        "equity": equity,
        "total_pnl": equity - paper_account.starting_balance,
        "total_pnl_percent": ((equity / paper_account.starting_balance) - 1) * 100,
        "positions": serialized_positions,
        "trades": [serialize_trade(trade) for trade in trades],
    }


@router.get("/portfolio", response_model=PaperPortfolioResponse)
async def get_portfolio(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    return await portfolio(db)


@router.post("/orders", response_model=PaperPortfolioResponse)
async def create_order(
    order: PaperOrderCreate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    paper_account = await account(db)
    current_prices = await prices()
    symbol = order.symbol.upper()
    price = current_prices.get(symbol)
    if price is None:
        raise HTTPException(400, "Marknaden stöds inte")

    side = order.side.lower()
    if side == "buy":
        if order.amount_usdt > paper_account.cash_balance:
            raise HTTPException(400, "Otillräckligt paper-saldo")
        quantity = order.amount_usdt / price
        paper_account.cash_balance -= order.amount_usdt
        position = PaperPosition(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            stop_loss=(
                price * (1 - order.stop_loss_percent / 100) if order.stop_loss_percent else None
            ),
            take_profit=(
                price * (1 + order.take_profit_percent / 100) if order.take_profit_percent else None
            ),
        )
        db.add(position)
        db.add(
            PaperTrade(
                symbol=symbol,
                side="BUY",
                quantity=quantity,
                price=price,
                reason="Manuell paper-order",
            )
        )
    elif side == "sell":
        position = (
            await db.scalars(
                select(PaperPosition)
                .where(PaperPosition.symbol == symbol)
                .order_by(PaperPosition.opened_at)
            )
        ).first()
        if position is None:
            raise HTTPException(400, "Ingen öppen position att sälja")
        proceeds = position.quantity * price
        realized_pnl = (price - position.entry_price) * position.quantity
        paper_account.cash_balance += proceeds
        db.add(
            PaperTrade(
                symbol=symbol,
                side="SELL",
                quantity=position.quantity,
                price=price,
                realized_pnl=realized_pnl,
                reason="Manuell stängning",
            )
        )
        await db.delete(position)
    else:
        raise HTTPException(400, "side måste vara buy eller sell")

    await db.commit()
    return await portfolio(db)


@router.post("/reset", response_model=PaperPortfolioResponse)
async def reset(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    for model in (PaperPosition, PaperTrade):
        rows = (await db.scalars(select(model))).all()
        for row in rows:
            await db.delete(row)
    paper_account = await account(db)
    paper_account.cash_balance = paper_account.starting_balance
    await db.commit()
    return await portfolio(db)
