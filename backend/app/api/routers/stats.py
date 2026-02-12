"""
Stats API Router - PnL and Capital Overview
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.session import get_db
from app.db.models import Lot, Fill, Configuration, DailySnapshot
from app.config import settings

router = APIRouter(prefix="/stats", tags=["stats"])


class CapitalSummary(BaseModel):
    starting_capital: float
    current_capital: float
    net_change_usd: float
    net_change_pct: float
    deployed_capital: float  # In active lots
    available_capital: float
    unrealized_pnl: float  # Potential profit if all lots sold now


class PnLBreakdown(BaseModel):
    today_pnl: float
    today_pct: float
    week_pnl: float
    week_pct: float
    month_pnl: float
    month_pct: float
    year_pnl: float
    year_pct: float
    lifetime_pnl: float
    lifetime_pct: float
    

class DailyPnLPoint(BaseModel):
    date: str
    pnl: float
    cumulative: float


class PnLHistory(BaseModel):
    daily_pnl: List[DailyPnLPoint]


@router.get("/capital-summary", response_model=CapitalSummary)
async def get_capital_summary(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Returns starting capital, current capital, net change, and allocation.
    Starting capital is auto-detected from first trade.
    """
    # Get lifetime realized PnL from closed lots
    lifetime_result = await db.execute(
        select(func.coalesce(func.sum(Lot.realized_pnl), 0.0))
        .where(Lot.status == "CLOSED")
    )
    lifetime_pnl = lifetime_result.scalar() or 0.0
    
    # Get deployed capital (sum of buy_cost for OPEN lots)
    deployed_result = await db.execute(
        select(func.coalesce(func.sum(Lot.buy_cost), 0.0))
        .where(Lot.status == "OPEN")
    )
    deployed_capital = deployed_result.scalar() or 0.0
    
    # Auto-detect starting capital from budget setting
    # For MVP: use configuration or default
    starting_capital_result = await db.execute(
        select(Configuration.value).where(Configuration.key == "budget")
    )
    starting_capital_str = starting_capital_result.scalar()
    
    if starting_capital_str:
        starting_capital = float(starting_capital_str)
    else:
        # Fallback to old key if budget not found
        old_cap_result = await db.execute(
            select(Configuration.value).where(Configuration.key == "starting_capital")
        )
        old_cap_str = old_cap_result.scalar()
        if old_cap_str:
            starting_capital = float(old_cap_str)
        else:
            # use default
            starting_capital = 10000.0  # Default paper capital
    
    # Calculate unrealized PnL (Mark-to-Market)
    # Fetch all open lots to calculate actual value vs cost
    lots_res = await db.execute(select(Lot).where(Lot.status == "OPEN"))
    open_lots = lots_res.scalars().all()
    
    unrealized_pnl = 0.0
    
    if open_lots:
        # Group by market to minimize API calls
        market_lots = {}
        for lot in open_lots:
            if lot.market_id not in market_lots:
                market_lots[lot.market_id] = []
            market_lots[lot.market_id].append(lot)
            
        # Use the engine's adapter (respects Paper/Mock/Coinbase mode)
        adapter = request.app.state.bot_engine.adapter if hasattr(request.app.state, "bot_engine") else None
        
        for market_id, lots in market_lots.items():
            try:
                current_price = await adapter.get_ticker(market_id)
                
                for lot in lots:
                    # Mark-to-Market: (Current Price * Size) - Buy Cost
                    market_value = current_price * lot.buy_size
                    pnl = market_value - lot.buy_cost
                    unrealized_pnl += pnl
            except Exception as e:
                # If price fetch fails, ignore this market's pnl contribution (safer than crashing)
                pass
    
    # Current capital = starting + realized PnL
    current_capital = starting_capital + lifetime_pnl
    available_capital = starting_capital - deployed_capital + lifetime_pnl
    
    net_change_usd = lifetime_pnl
    net_change_pct = (net_change_usd / starting_capital * 100) if starting_capital > 0 else 0
    
    return CapitalSummary(
        starting_capital=starting_capital,
        current_capital=current_capital,
        net_change_usd=net_change_usd,
        net_change_pct=net_change_pct,
        deployed_capital=deployed_capital,
        available_capital=available_capital,
        unrealized_pnl=unrealized_pnl
    )


@router.get("/pnl-breakdown", response_model=PnLBreakdown)
async def get_pnl_breakdown(db: AsyncSession = Depends(get_db)):
    """
    Returns PnL for today, this week, this month, this year, and lifetime.
    """
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate week start (Monday)
    week_start = today_start - timedelta(days=now.weekday())
    
    # Month start
    month_start = today_start.replace(day=1)
    
    # Year start
    year_start = today_start.replace(month=1, day=1)
    
    # Helper to get PnL for a time period
    async def get_pnl_since(since: datetime) -> float:
        result = await db.execute(
            select(func.coalesce(func.sum(Lot.realized_pnl), 0.0))
            .where(Lot.status == "CLOSED")
            .where(Lot.buy_time >= since)
        )
        return result.scalar() or 0.0
    
    # Lifetime PnL
    lifetime_result = await db.execute(
        select(func.coalesce(func.sum(Lot.realized_pnl), 0.0))
        .where(Lot.status == "CLOSED")
    )
    lifetime_pnl = lifetime_result.scalar() or 0.0
    
    # Get PnL for each period
    today_pnl = await get_pnl_since(today_start)
    week_pnl = await get_pnl_since(week_start)
    month_pnl = await get_pnl_since(month_start)
    year_pnl = await get_pnl_since(year_start)
    
    # Get starting capital for percentage calculations
    starting_capital_result = await db.execute(
        select(Configuration.value).where(Configuration.key == "budget")
    )
    starting_capital_str = starting_capital_result.scalar()
    if not starting_capital_str:
        # Fallback to old key
        old_result = await db.execute(
            select(Configuration.value).where(Configuration.key == "starting_capital")
        )
        starting_capital_str = old_result.scalar()
    starting_capital = float(starting_capital_str) if starting_capital_str else 10000.0
    
    # Calculate percentages
    def calc_pct(pnl: float) -> float:
        return (pnl / starting_capital * 100) if starting_capital > 0 else 0.0
    
    return PnLBreakdown(
        today_pnl=today_pnl,
        today_pct=calc_pct(today_pnl),
        week_pnl=week_pnl,
        week_pct=calc_pct(week_pnl),
        month_pnl=month_pnl,
        month_pct=calc_pct(month_pnl),
        year_pnl=year_pnl,
        year_pct=calc_pct(year_pnl),
        lifetime_pnl=lifetime_pnl,
        lifetime_pct=calc_pct(lifetime_pnl)
    )


@router.get("/pnl-history", response_model=PnLHistory)
async def get_pnl_history(days: int = 30, db: AsyncSession = Depends(get_db)):
    """
    Returns daily PnL for the last N days (for sparkline chart).
    """
    now = datetime.now()
    start_date = now - timedelta(days=days)
    
    # Get snapshots if available
    snapshot_result = await db.execute(
        select(DailySnapshot)
        .where(DailySnapshot.date >= start_date.strftime("%Y-%m-%d"))
        .order_by(DailySnapshot.date.asc())
    )
    snapshots = snapshot_result.scalars().all()
    
    if snapshots:
        return PnLHistory(
            daily_pnl=[
                DailyPnLPoint(
                    date=s.date,
                    pnl=s.realized_pnl,
                    cumulative=s.cumulative_pnl
                )
                for s in snapshots
            ]
        )
    
    # Fallback: Calculate from lots grouped by day
    daily_pnl_result = await db.execute(
        select(
            func.date(Lot.buy_time).label('date'),
            func.sum(Lot.realized_pnl).label('pnl')
        )
        .where(Lot.status == "CLOSED")
        .where(Lot.buy_time >= start_date)
        .group_by(func.date(Lot.buy_time))
        .order_by(func.date(Lot.buy_time).asc())
    )
    rows = daily_pnl_result.all()
    
    # Build cumulative
    cumulative = 0.0
    daily_points = []
    for row in rows:
        cumulative += row.pnl or 0.0
        daily_points.append(DailyPnLPoint(
            date=str(row.date),
            pnl=row.pnl or 0.0,
            cumulative=cumulative
        ))
    
    return PnLHistory(daily_pnl=daily_points)
