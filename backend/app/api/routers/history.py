from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.db.models import Fill
from app.schemas import ConfigDict, BaseModel
from datetime import datetime

class FillResponse(BaseModel):
    id: str
    order_id: str
    market_id: str
    side: str
    price: float
    size: float
    fee: float
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/fills", response_model=List[FillResponse])
async def list_fills(market_id: str = None, db: AsyncSession = Depends(get_db)):
    query = select(Fill).order_by(Fill.timestamp.desc())
    if market_id:
        query = query.where(Fill.market_id == market_id)
    
    result = await db.execute(query)
    return result.scalars().all()
