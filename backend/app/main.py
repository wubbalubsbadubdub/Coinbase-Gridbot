from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
import asyncio
import logging
from app.config import settings
from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from sqlalchemy import select
from app.db import models
from app.exchanges.coinbase import CoinbaseAdapter
from app.exchanges.mock import MockAdapter
from app.bot.engine import BotEngine
from app.api.routers import markets, bot, orders, lots, config, control, history, seed
from app.api.websockets import ConnectionManager

# Global Bot Instance and WS Manager
bot_engine = None
ws_manager = ConnectionManager()

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.exchanges.coinbase import CoinbaseAdapter
    from app.exchanges.mock import MockAdapter
    from app.exchanges.paper import PaperWrapper
    from app.bot.engine import BotEngine
    from app.db.session import AsyncSessionLocal

    # Startup: Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Exchange Adapter
    if settings.EXCHANGE_TYPE == "coinbase":
        base_adapter = CoinbaseAdapter()
    else:
        base_adapter = MockAdapter()
    
    # Paper Mode Wrapper
    if settings.PAPER_MODE:
        logger.info("PAPER MODE ENABLED: Wrapping adapter.")
        adapter = PaperWrapper(base_adapter)
    else:
        adapter = base_adapter

    # Sync Markets from Adapter to DB (Critical for Mock data visualization)
    try:
        products = await adapter.get_products()
        async with AsyncSessionLocal() as session:
            # Fetch existing to avoid duplicates
            result = await session.execute(select(models.Market))
            existing_ids = {m.id for m in result.scalars().all()}
            
            for p in products:
                if p["id"] not in existing_ids:
                    # Enable mock markets by default for better UX
                    is_enabled = (settings.EXCHANGE_TYPE == "mock")
                    new_market = models.Market(id=p["id"], enabled=is_enabled, market_rank=0)
                    session.add(new_market)
            
            await session.commit()
    except Exception as e:
        print(f"Failed to sync markets: {e}")
        
    # Initialize Bot Engine
    global bot_engine
    bot_engine = BotEngine(adapter, AsyncSessionLocal, ws_manager)
    app.state.bot_engine = bot_engine
    
    # Start Bot Loop in Background
    asyncio.create_task(bot_engine.run_loop())
    
    yield
    # Shutdown: Dispose engine
    await engine.dispose()

app = FastAPI(title="Coinbase Gridbot", lifespan=lifespan)

# Routers
app.include_router(markets.router, prefix="/api")
app.include_router(bot.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(lots.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(control.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(seed.router, prefix="/api")

@app.get("/healthz")
async def healthz():
    """Health check endpoint."""
    return {"status": "ok", "env": settings.ENV}

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
             # Keep connection alive, maybe listen for client commands later
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
