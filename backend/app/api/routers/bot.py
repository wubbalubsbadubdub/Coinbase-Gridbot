from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Market
from app.schemas import BotStatus
from app.config import settings
# Import globals using a getter or direct import if careful about circular deps.
# main.py imports routers, so routers shouldn't import main.
# We need a way to check if loop is running. 
# For MVP, we'll just check settings and DB.
# Advanced: We could have a singleton 'State' object. 

router = APIRouter(prefix="/bot", tags=["bot"])

@router.get("/status", response_model=BotStatus)
async def get_bot_status(db: AsyncSession = Depends(get_db)):
    # Count enabled markets
    result = await db.execute(select(func.count(Market.id)).where(Market.enabled == True))
    active_count = result.scalar() or 0
    
    # Check if loop is "likely" running (naive check)
    # Ideally we'd ask the BotEngine instance. 
    # But since that's in main.py, it's hard to reach from here without circular imports.
    # We will report the CONFIG status for 'running'.
    
    return BotStatus(
        env=settings.ENV,
        live_trading=settings.LIVE_TRADING_ENABLED,
        exchange_type=settings.EXCHANGE_TYPE,
        paper_mode=settings.PAPER_MODE,
        running=True, # It's a background task for now, assumed running if app is up
        active_markets=active_count
    )
