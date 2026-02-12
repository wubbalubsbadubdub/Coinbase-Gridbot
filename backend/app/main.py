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
from app.api.routers import markets, bot, orders, lots, config, control, history, seed, stats
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
                product_id = p.get("product_id") or p.get("id")  # Support both formats
                if product_id and product_id not in existing_ids:
                    # Enable mock markets by default for better UX
                    is_enabled = (settings.EXCHANGE_TYPE == "mock")
                    new_market = models.Market(id=product_id, enabled=is_enabled, market_rank=0)
                    session.add(new_market)
            
            await session.commit()
    except Exception as e:
        print(f"Failed to sync markets: {e}")
        
    # Initialize Bot Engine
    global bot_engine
    bot_engine = BotEngine(adapter, AsyncSessionLocal, ws_manager)
    app.state.bot_engine = bot_engine
    
    # Load saved configuration from database
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            from app.db.models import Configuration
            
            async def get_cfg(key, default):
                result = await session.execute(
                    select(Configuration.value).where(Configuration.key == key)
                )
                val = result.scalar()
                return val if val is not None else default
            
            # Load persisted config
            grid_step = float(await get_cfg("grid_step_pct", "0.0033"))
            staging_band = float(await get_cfg("staging_band_depth_pct", "0.02"))
            max_orders = int(await get_cfg("max_open_orders", "10"))
            buffer_enabled = (await get_cfg("buffer_enabled", "false")).lower() == "true"
            buffer_pct = float(await get_cfg("buffer_pct", "0.01"))
            profit_mode = await get_cfg("profit_mode", "STEP")
            custom_profit = float(await get_cfg("custom_profit_pct", "0.01"))
            monthly_target = float(await get_cfg("monthly_profit_target_usd", "1000.0"))
            budget = float(await get_cfg("budget", "1000.0"))
            # NEW: Sizing config
            sizing_mode = await get_cfg("sizing_mode", "BUDGET_SPLIT")
            fixed_usd = float(await get_cfg("fixed_usd_per_trade", "10.0"))
            capital_pct = float(await get_cfg("capital_pct_per_trade", "1.0"))
            
            # Apply to engine
            bot_engine.update_config(
                grid_step_pct=grid_step,
                staging_band_depth_pct=staging_band,
                max_open_orders=max_orders,
                buffer_enabled=buffer_enabled,
                buffer_pct=buffer_pct,
                profit_mode=profit_mode,
                custom_profit_pct=custom_profit,
                monthly_profit_target_usd=monthly_target,
                budget=budget,
                sizing_mode=sizing_mode,
                fixed_usd_per_trade=fixed_usd,
                capital_pct_per_trade=capital_pct
            )
            logger.info(f"Loaded saved config: sizing_mode={sizing_mode}, fixed_usd={fixed_usd}, capital_pct={capital_pct}")
    except Exception as e:
        logger.warning(f"Failed to load saved config: {e}")
    
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
app.include_router(stats.router, prefix="/api")

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
