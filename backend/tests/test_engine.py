import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.db.base import Base
from app.db.models import Market, Order, BotState
from app.bot.engine import BotEngine
from app.exchanges.mock import MockAdapter

# In-memory DB for Engine Test
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def test_session_factory():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()

@pytest.mark.asyncio
async def test_engine_tick_flow(test_session_factory):
    # 1. Setup
    adapter = MockAdapter()
    engine = BotEngine(adapter, test_session_factory)
    
    # Set mock price
    adapter.set_mock_price("BTC-USD", 50000.0)
    
    async with test_session_factory() as session:
        # 2. Seed Market
        market = Market(id="BTC-USD", enabled=True)
        session.add(market)
        await session.commit()
    
    # 3. Trigger Tick (Manually, not via loop)
    async with test_session_factory() as session:
        await engine.tick(session)
        # Verify Anchor State Created
        res = await session.execute(select(BotState).where(BotState.key == "BTC-USD_anchor"))
        state = res.scalar_one_or_none()
        assert state is not None
        assert state.value["price"] == 50000.0
        
        # Verify Orders Placed (Grid Calculation)
        # 50,000 * (1 - 0.0033) approx 49,835
        orders_res = await session.execute(select(Order).where(Order.market_id == "BTC-USD"))
        orders = orders_res.scalars().all()
        assert len(orders) > 0
        assert orders[0].side == "BUY"
        assert orders[0].status == "OPEN"
        
    # 4. Trigger Update (Price Drops)
    adapter.set_mock_price("BTC-USD", 45000.0) # Huge drop
    async with test_session_factory() as session:
        await engine.tick(session)
        # Should NOT rebase downwards (Add-Only logic)
        res = await session.execute(select(BotState).where(BotState.key == "BTC-USD_anchor"))
        state = res.scalar_one()
        assert state.value["price"] == 50000.0 # Anchor stays high
        
        # Should place deep buy orders around 45k
