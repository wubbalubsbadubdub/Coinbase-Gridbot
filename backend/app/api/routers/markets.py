from fastapi import APIRouter, Depends, HTTPException, Request
import fastapi
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.db.models import Market, BotState
from app.schemas import MarketResponse, MarketUpdate

router = APIRouter(prefix="/markets", tags=["markets"])

@router.get("/", response_model=List[MarketResponse])
async def list_markets(favorites_only: bool = False, db: AsyncSession = Depends(get_db)):
    query = select(Market)
    if favorites_only:
        query = query.where(Market.is_favorite == True)
    
    # Sort by Rank (lower is better) or Volume? Spec says Volume/Cap.
    # Let's sort by enabled first (Active), then Favorite, then Rank.
    query = query.order_by(Market.enabled.desc(), Market.is_favorite.desc(), Market.market_rank.asc())
    
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/all-pairs")
async def list_all_pairs(request: fastapi.Request):
    """
    Proxies to Exchange Adapter to get ALL available products.
    """
    if hasattr(request.app.state, "bot_engine") and request.app.state.bot_engine:
        adapter = request.app.state.bot_engine.adapter
        # adapter.get_products() is async
        try:
            products = await adapter.get_products()
            # product format depends on adapter. Coinbase returns dicts.
            # We filter for USD pairs only for simplicity? Or return all.
            # Spec says "All available Coinbase pairs".
            return products
        except Exception as e:
             raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")
    
    return []

@router.post("/{market_id}/favorite")
async def toggle_favorite(market_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Market).where(Market.id == market_id))
    market = result.scalar_one_or_none()
    
    if not market:
        # Lazy Create
        market = Market(id=market_id, is_favorite=True, enabled=False)
        db.add(market)
        await db.commit()
        return {"status": "created_and_favorited", "is_favorite": True}
    
    market.is_favorite = not market.is_favorite
    await db.commit()
    return {"status": "success", "is_favorite": market.is_favorite}

@router.post("/{market_id}/start")
async def start_market(market_id: str, db: AsyncSession = Depends(get_db)):
    # 1. Highlander Rule: Stop ALL other markets
    # Fetch currently enabled markets
    result = await db.execute(select(Market).where(Market.enabled == True))
    running_markets = result.scalars().all()
    
    for m in running_markets:
        if m.id != market_id:
            m.enabled = False 
    
    # 2. Enable Target
    result = await db.execute(select(Market).where(Market.id == market_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Market not found")
        
    target.enabled = True
    
    await db.commit()
    return {"status": "started", "market_id": market_id}

@router.post("/{market_id}/stop")
async def stop_market(market_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import update
    from app.db.models import Order
    
    result = await db.execute(select(Market).where(Market.id == market_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Market not found")
    
    # 1. Disable the market
    target.enabled = False
    
    # 2. Collect open order IDs BEFORE bulk-canceling in DB
    open_orders_result = await db.execute(
        select(Order.id)
        .where(Order.market_id == market_id)
        .where(Order.status == "OPEN")
    )
    open_order_ids = [row[0] for row in open_orders_result.all()]
    
    # 3. Cancel all open orders for this market in the database
    await db.execute(
        update(Order)
        .where(Order.market_id == market_id)
        .where(Order.status == "OPEN")
        .values(status="CANCELED")
    )
    
    # 4. Cancel orders on the exchange (paper/live)
    if hasattr(request.app.state, "bot_engine") and request.app.state.bot_engine:
        for order_id in open_order_ids:
            try:
                await request.app.state.bot_engine.adapter.cancel_order(order_id)
            except Exception:
                pass  # Order may already be canceled/filled on exchange
    
    await db.commit()
    return {"status": "stopped", "market_id": market_id, "orders_canceled": True}

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
        raise HTTPException(status_code=404, detail="Market not found")

    if update.enabled is not None:
        # If enabling via PATCH, we should probably also enforce Highlander, 
        # but for safety let's assume PATCH is raw edit. 
        # Ideally frontend uses /start, but if it uses PATCH, we might have multiple running.
        # Let's enforce it here too just to be safe?
        # User spec said "When user sends START command...". 
        # Let's leave PATCH as raw override for power users/debugging.
        market.enabled = update.enabled
        
    if update.ranking is not None:
        market.ranking = update.ranking
    if update.settings is not None:
        market.settings = update.settings
        
    await db.commit()
    await db.refresh(market)
    return market
