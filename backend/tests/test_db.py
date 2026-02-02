import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.db.models import Order, Market
from sqlalchemy import select

# Use strictly in-memory DB for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def test_engine():
    # Create a new engine for each test function to ensure total isolation
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(test_engine):
    # Create a session bound to the test engine
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.mark.asyncio
async def test_create_market_and_order(db_session):
    # 1. Create a Market
    market = Market(id="BTC-USD", enabled=True, market_rank=1)
    db_session.add(market)
    await db_session.commit()
    
    # 2. Create an Order linked to the Market
    order = Order(
        id="ord_123",
        market_id="BTC-USD",
        side="BUY",
        price=50000.0,
        size=0.1,
        status="OPEN"
    )
    db_session.add(order)
    await db_session.commit()

    # 3. Read back
    result = await db_session.execute(select(Order).where(Order.id == "ord_123"))
    fetched_order = result.scalar_one()
    
    assert fetched_order.market_id == "BTC-USD"
    assert fetched_order.price == 50000.0

