from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class MarketBase(BaseModel):
    id: str
    enabled: bool = False
    is_favorite: bool = False
    market_rank: int = 999999
    volume_24h: float = 0.0
    ranking: int = 0
    settings: Optional[Dict[str, Any]] = None

class MarketCreate(MarketBase):
    pass

class MarketResponse(MarketBase):
    last_updated: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class ConfigUpdate(BaseModel):
    grid_step_pct: Optional[float] = None
    budget: Optional[float] = None
    max_open_orders: Optional[int] = None
    staging_band_depth_pct: Optional[float] = None
    profit_mode: Optional[str] = None # "STEP", "STEP_REINVEST", "CUSTOM", "SMART_REINVEST"
    buffer_enabled: Optional[bool] = None
    buffer_pct: Optional[float] = None
    custom_profit_pct: Optional[float] = None
    monthly_profit_target_usd: Optional[float] = None
    # NEW: Trade sizing options
    sizing_mode: Optional[str] = None  # "BUDGET_SPLIT", "FIXED_USD", "CAPITAL_PCT"
    fixed_usd_per_trade: Optional[float] = None
    capital_pct_per_trade: Optional[float] = None

class MarketUpdate(BaseModel):
    enabled: Optional[bool] = None
    ranking: Optional[int] = None
    settings: Optional[Dict[str, Any]] = None

class BotStatus(BaseModel):
    env: str
    live_trading: bool
    exchange_type: str
    paper_mode: bool
    running: bool
    active_markets: int

class OrderResponse(BaseModel):
    id: str
    market_id: str
    side: str
    price: float
    size: float
    status: str
    client_tag: Optional[str] = None
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class LotResponse(BaseModel):
    id: int
    market_id: str
    buy_order_id: str
    buy_price: float
    buy_size: float
    buy_time: Optional[datetime] = None
    sell_order_id: Optional[str] = None
    sell_price: Optional[float] = None
    status: str
    realized_pnl: float = 0.0
    model_config = ConfigDict(from_attributes=True)
