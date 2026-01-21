from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict, Any

from app.schemas import ConfigUpdate

router = APIRouter(prefix="/config", tags=["config"])

@router.get("/")
async def get_config(request: Request):
    """
    Get current running configuration.
    """
    if hasattr(request.app.state, "bot_engine") and request.app.state.bot_engine:
        # Return strategy config
        # Ideally, we should persist this in DB as well, but for MVP we read from memory/defaults
        strategy = request.app.state.bot_engine.strategy
        return {
            "grid_step_pct": strategy.grid_step_pct,
            "staging_band_pct": strategy.staging_band_pct,
            "max_open_orders": strategy.max_orders,
            "buffer_enabled": strategy.buffer_enabled,
            "buffer_pct": strategy.buffer_pct,
            # "budget": ... # We don't track budget in strategy yet
        }
    return {"error": "Bot engine not initialized"}

@router.post("/")
async def update_config(config: ConfigUpdate, request: Request):
    """
    Update configuration hot.
    """
    # Update Engine
    if request.app.state.bot_engine:
        request.app.state.bot_engine.update_config(
            grid_step_pct=config.grid_step_pct,
            budget=config.budget,
            max_open_orders=config.max_open_orders,
            staging_band_depth_pct=config.staging_band_depth_pct,
            buffer_enabled=config.buffer_enabled,
            buffer_pct=config.buffer_pct,
            profit_mode=config.profit_mode
        )
        return {"status": "updated", "config": config}
    
    raise HTTPException(status_code=503, detail="Bot engine not ready")
