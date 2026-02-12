from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.db.session import get_db
from app.db.models import Order
from app.schemas import OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    market_id: Optional[str] = None, 
    status: Optional[str] = "OPEN", 
    limit: int = 30,
    skip: int = 0,
    db: AsyncSession = Depends(get_db)
):
    query = select(Order)
    if market_id:
        query = query.where(Order.market_id == market_id)
    if status != "ALL":
        query = query.where(Order.status == status)
    
    query = query.order_by(Order.created_at.desc()).limit(limit).offset(skip)
    result = await db.execute(query)
    return result.scalars().all()

@router.delete("/{order_id}")
async def cancel_order(order_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    # 1. Fetch Order
    result = await db.execute(select(Order).where(Order.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # 2. Call Exchange via Engine stored in App State
    if hasattr(request.app.state, "bot_engine") and request.app.state.bot_engine:
        try:
             # Use the engine's adapter directly
            await request.app.state.bot_engine.adapter.cancel_order(order_id)
        except Exception as e:
            # If it fails (e.g. already filled), log it but proceed to cancel in DB?
            print(f"Failed to cancel on exchange: {e}")

    # 3. Update DB
    order.status = "CANCELED"
    await db.commit()
    return {"status": "success", "id": order_id}
