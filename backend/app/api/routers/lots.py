from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.db.session import get_db
from app.db.models import Lot
from app.schemas import LotResponse

router = APIRouter(prefix="/lots", tags=["lots"])

@router.get("/", response_model=List[LotResponse])
async def list_lots(db: AsyncSession = Depends(get_db)):
    # Return all active lots (OPEN)
    result = await db.execute(select(Lot).where(Lot.status == "OPEN").order_by(Lot.buy_timestamp.desc()))
    return result.scalars().all()
