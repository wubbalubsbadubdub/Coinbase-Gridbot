import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app.db.session import get_db
from app.db.models import Market

# Setup In-Memory DB for API Tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture
async def api_db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session
    
    await engine.dispose()

@pytest.fixture
async def client(api_db_session):
    # Override the dependency
    async def override_get_db():
        yield api_db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Use ASGITransport to test FastAPI app directly without running server
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_get_bot_status(client):
    response = await client.get("/api/bot/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data
    assert "active_markets" in data
    assert data["active_markets"] == 0

@pytest.mark.asyncio
async def test_market_crud(client, api_db_session):
    # 1. Seed a market
    market = Market(id="BTC-USD", enabled=False, ranking=1)
    api_db_session.add(market)
    await api_db_session.commit()
    
    # 2. List markets
    resp = await client.get("/api/markets/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == "BTC-USD"
    assert data[0]["enabled"] is False
    
    # 3. Enable Market
    resp = await client.patch("/api/markets/BTC-USD", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True
    
    # 4. Verify Status Change
    resp = await client.get("/api/bot/status")
    assert resp.json()["active_markets"] == 1
