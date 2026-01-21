from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.db.models import Market, BotState
from app.schemas import MarketResponse, MarketUpdate

router = APIRouter(prefix="/markets", tags=["markets"])

@router.get("/", response_model=List[MarketResponse])
async def list_markets(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Market).order_by(Market.ranking))
    return result.scalars().all()

@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market

@router.patch("/{market_id}", response_model=MarketResponse)
async def update_market(market_id: str, update: MarketUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    
    if not market:
        # Check if we should create it on the fly? 
        # For now, simplistic approach: if setting enabled/ranking, assume it exists or fail.
        # But wait, our check_db script created ETH-USD. 
        # If user wants to enable a NEW market, they might need to 'create' it or we autoscan.
        # Let's assume manual creation or autoscan is separate. Failing 404 is safe.
        raise HTTPException(status_code=404, detail="Market not found")

    if update.enabled is not None:
        market.enabled = update.enabled
    if update.ranking is not None:
        market.ranking = update.ranking
    if update.settings is not None:
        market.settings = update.settings
        
    await db.commit()
    await db.refresh(market)
    return market
