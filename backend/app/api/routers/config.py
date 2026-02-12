from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.schemas import ConfigUpdate
from app.db.session import get_db
from app.db.models import Configuration

router = APIRouter(prefix="/config", tags=["config"])

# Helper function to get config value from database
async def get_config_value(db: AsyncSession, key: str, default=None):
    result = await db.execute(
        select(Configuration.value).where(Configuration.key == key)
    )
    value = result.scalar()
    return value if value is not None else default

# Helper function to set config value in database
async def set_config_value(db: AsyncSession, key: str, value: str):
    result = await db.execute(
        select(Configuration).where(Configuration.key == key)
    )
    config = result.scalar_one_or_none()
    
    if config:
        config.value = str(value)
    else:
        config = Configuration(key=key, value=str(value))
        db.add(config)
    
    await db.commit()

@router.get("/")
async def get_config(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Get current running configuration.
    Reads from engine (in-memory) but falls back to database for persistence.
    """
    # Load persisted config from database
    buffer_enabled_str = await get_config_value(db, "buffer_enabled", "false")
    buffer_pct_str = await get_config_value(db, "buffer_pct", "0.01")
    grid_step_pct_str = await get_config_value(db, "grid_step_pct", "0.0033")
    staging_band_str = await get_config_value(db, "staging_band_depth_pct", "0.02")
    max_orders_str = await get_config_value(db, "max_open_orders", "10")
    profit_mode_str = await get_config_value(db, "profit_mode", "STEP")
    custom_profit_pct_str = await get_config_value(db, "custom_profit_pct", "0.01")
    monthly_target_str = await get_config_value(db, "monthly_profit_target_usd", "1000.0")
    budget_str = await get_config_value(db, "budget", "1000.0")
    # NEW: Sizing config
    sizing_mode_str = await get_config_value(db, "sizing_mode", "BUDGET_SPLIT")
    fixed_usd_str = await get_config_value(db, "fixed_usd_per_trade", "10.0")
    capital_pct_str = await get_config_value(db, "capital_pct_per_trade", "1.0")
    
    if hasattr(request.app.state, "bot_engine") and request.app.state.bot_engine:
        # Return strategy config (prioritize engine state, but sync with DB)
        strategy = request.app.state.bot_engine.strategy
        return {
            "grid_step_pct": strategy.grid_step_pct,
            "staging_band_depth_pct": strategy.staging_band_pct,
            "max_open_orders": strategy.max_orders,
            "buffer_enabled": strategy.buffer_enabled,
            "buffer_pct": strategy.buffer_pct,
            "profit_mode": getattr(strategy, "profit_mode", "STEP"),
            "custom_profit_pct": getattr(strategy, "custom_profit_pct", 0.01),
            "monthly_profit_target_usd": getattr(strategy, "monthly_profit_target_usd", 1000.0),
            "budget": getattr(strategy, "budget", 1000.0),
            # NEW: Sizing config
            "sizing_mode": getattr(strategy, "sizing_mode", "BUDGET_SPLIT"),
            "fixed_usd_per_trade": getattr(strategy, "fixed_usd_per_trade", 10.0),
            "capital_pct_per_trade": getattr(strategy, "capital_pct_per_trade", 1.0)
        }
    
    # Return from database if engine not running
    return {
        "grid_step_pct": float(grid_step_pct_str),
        "staging_band_depth_pct": float(staging_band_str),
        "max_open_orders": int(max_orders_str),
        "buffer_enabled": buffer_enabled_str.lower() == "true",
        "buffer_pct": float(buffer_pct_str),
        "profit_mode": profit_mode_str,
        "custom_profit_pct": float(custom_profit_pct_str),
        "monthly_profit_target_usd": float(monthly_target_str),
        "budget": float(budget_str),
        # NEW: Sizing config
        "sizing_mode": sizing_mode_str,
        "fixed_usd_per_trade": float(fixed_usd_str),
        "capital_pct_per_trade": float(capital_pct_str)
    }

@router.post("/")
async def update_config(config: ConfigUpdate, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Update configuration and persist to database.
    """
    # Persist to database for restart survival
    if config.buffer_enabled is not None:
        await set_config_value(db, "buffer_enabled", str(config.buffer_enabled).lower())
    
    if config.buffer_pct is not None:
        await set_config_value(db, "buffer_pct", str(config.buffer_pct))
    
    if config.grid_step_pct is not None:
        await set_config_value(db, "grid_step_pct", str(config.grid_step_pct))
    
    if config.staging_band_depth_pct is not None:
        await set_config_value(db, "staging_band_depth_pct", str(config.staging_band_depth_pct))
    
    if config.max_open_orders is not None:
        await set_config_value(db, "max_open_orders", str(config.max_open_orders))
    
    if config.profit_mode is not None:
        await set_config_value(db, "profit_mode", str(config.profit_mode))
    
    if config.custom_profit_pct is not None:
        await set_config_value(db, "custom_profit_pct", str(config.custom_profit_pct))
    
    if config.monthly_profit_target_usd is not None:
        await set_config_value(db, "monthly_profit_target_usd", str(config.monthly_profit_target_usd))
    
    if config.budget is not None:
        await set_config_value(db, "budget", str(config.budget))
    
    # NEW: Sizing config persistence
    if config.sizing_mode is not None:
        await set_config_value(db, "sizing_mode", str(config.sizing_mode))
    
    if config.fixed_usd_per_trade is not None:
        await set_config_value(db, "fixed_usd_per_trade", str(config.fixed_usd_per_trade))
    
    if config.capital_pct_per_trade is not None:
        await set_config_value(db, "capital_pct_per_trade", str(config.capital_pct_per_trade))
    
    # Update Engine (in-memory)
    if request.app.state.bot_engine:
        request.app.state.bot_engine.update_config(
            grid_step_pct=config.grid_step_pct,
            budget=config.budget,
            max_open_orders=config.max_open_orders,
            staging_band_depth_pct=config.staging_band_depth_pct,
            buffer_enabled=config.buffer_enabled,
            buffer_pct=config.buffer_pct,
            profit_mode=config.profit_mode,
            custom_profit_pct=config.custom_profit_pct,
            monthly_profit_target_usd=config.monthly_profit_target_usd,
            sizing_mode=config.sizing_mode,
            fixed_usd_per_trade=config.fixed_usd_per_trade,
            capital_pct_per_trade=config.capital_pct_per_trade
        )
        return {"status": "updated", "config": config}
    
    raise HTTPException(status_code=503, detail="Bot engine not ready")
