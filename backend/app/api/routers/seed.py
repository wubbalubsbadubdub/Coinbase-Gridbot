"""
Seed endpoint for testing the Order Manager UI.
Creates fake orders, lots, and fills for development/testing.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete
from datetime import datetime, timedelta
import uuid

from app.db.session import get_db
from app.db.models import Order, Lot, Fill, Market

router = APIRouter()


@router.post("/seed-test-data")
async def seed_test_data(session: AsyncSession = Depends(get_db)):
    """
    Seeds the database with fake orders, lots, and fills for testing the UI.
    WARNING: This clears existing order/lot/fill data first!
    """
    # Clear existing test data
    await session.execute(delete(Fill))
    await session.execute(delete(Lot))
    await session.execute(delete(Order))
    
    # Ensure BTC-USD market exists
    market = await session.get(Market, "BTC-USD")
    if not market:
        market = Market(id="BTC-USD", enabled=False, is_favorite=True)
        session.add(market)
        await session.flush()
    
    now = datetime.utcnow()
    orders_created = []
    lots_created = []
    fills_created = []
    
    # ==========================================================
    # CREATE OPEN ORDERS (for "Open Orders" tab)
    # ==========================================================
    open_orders = [
        {"side": "BUY", "price": 44500.00, "size": 0.001},
        {"side": "BUY", "price": 44000.00, "size": 0.001},
        {"side": "BUY", "price": 43500.00, "size": 0.002},
        {"side": "SELL", "price": 46000.00, "size": 0.001},
        {"side": "SELL", "price": 46500.00, "size": 0.001},
    ]
    
    for o in open_orders:
        order = Order(
            id=str(uuid.uuid4()),
            market_id="BTC-USD",
            side=o["side"],
            price=o["price"],
            size=o["size"],
            status="OPEN",
            client_tag="grid_order"
        )
        session.add(order)
        orders_created.append(order.id)
    
    # ==========================================================
    # CREATE FILLED ORDERS + LOTS (for "Active Lots" tab)
    # ==========================================================
    active_lots = [
        {"buy_price": 45000.00, "size": 0.001, "sell_price": 45150.00},
        {"buy_price": 44800.00, "size": 0.002, "sell_price": 44950.00},
        {"buy_price": 44600.00, "size": 0.001, "sell_price": 44750.00},
    ]
    
    for i, lot_data in enumerate(active_lots):
        # Create filled buy order
        buy_order = Order(
            id=str(uuid.uuid4()),
            market_id="BTC-USD",
            side="BUY",
            price=lot_data["buy_price"],
            size=lot_data["size"],
            status="FILLED",
            client_tag="grid_order"
        )
        session.add(buy_order)
        
        # Create pending sell order for this lot
        sell_order = Order(
            id=str(uuid.uuid4()),
            market_id="BTC-USD",
            side="SELL",
            price=lot_data["sell_price"],
            size=lot_data["size"],
            status="OPEN",
            client_tag="grid_order"
        )
        session.add(sell_order)
        await session.flush()
        
        # Create lot (OPEN = waiting for sell to fill)
        lot = Lot(
            market_id="BTC-USD",
            buy_order_id=buy_order.id,
            buy_price=lot_data["buy_price"],
            buy_size=lot_data["size"],
            buy_cost=lot_data["buy_price"] * lot_data["size"],
            buy_time=now - timedelta(hours=i+1),
            sell_order_id=sell_order.id,
            sell_price=lot_data["sell_price"],
            status="OPEN"
        )
        session.add(lot)
        lots_created.append(lot)
    
    # ==========================================================
    # CREATE CLOSED LOTS + FILLS (for "History" tab)
    # ==========================================================
    historical_trades = [
        {"side": "BUY", "price": 44200.00, "size": 0.001, "fee": 0.44, "hours_ago": 2},
        {"side": "SELL", "price": 44350.00, "size": 0.001, "fee": 0.44, "hours_ago": 1.5},
        {"side": "BUY", "price": 44100.00, "size": 0.002, "fee": 0.88, "hours_ago": 1},
        {"side": "SELL", "price": 44250.00, "size": 0.002, "fee": 0.88, "hours_ago": 0.5},
        {"side": "BUY", "price": 43950.00, "size": 0.001, "fee": 0.44, "hours_ago": 0.25},
    ]
    
    for trade in historical_trades:
        # Create the completed order
        order = Order(
            id=str(uuid.uuid4()),
            market_id="BTC-USD",
            side=trade["side"],
            price=trade["price"],
            size=trade["size"],
            status="FILLED",
            client_tag="grid_order"
        )
        session.add(order)
        await session.flush()
        
        # Create fill record
        fill = Fill(
            id=str(uuid.uuid4()),
            order_id=order.id,
            market_id="BTC-USD",
            side=trade["side"],
            price=trade["price"],
            size=trade["size"],
            fee=trade["fee"],
            timestamp=now - timedelta(hours=trade["hours_ago"])
        )
        session.add(fill)
        fills_created.append(fill.id)
    
    await session.commit()
    
    return {
        "success": True,
        "message": "Test data seeded successfully!",
        "data": {
            "open_orders": len(open_orders),
            "active_lots": len(active_lots),
            "historical_fills": len(historical_trades)
        }
    }


@router.delete("/clear-test-data")
async def clear_test_data(session: AsyncSession = Depends(get_db)):
    """Clears all orders, lots, and fills. Use with caution!"""
    await session.execute(delete(Fill))
    await session.execute(delete(Lot))
    await session.execute(delete(Order))
    await session.commit()
    
    return {"success": True, "message": "All order data cleared."}
