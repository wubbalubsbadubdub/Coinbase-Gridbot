from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Configuration(Base):
    __tablename__ = "config"
    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
    description = Column(String, nullable=True)

class Market(Base):
    __tablename__ = "markets"
    id = Column(String, primary_key=True)  # e.g., "BTC-USD"
    enabled = Column(Boolean, default=False)
    is_favorite = Column(Boolean, default=False)
    market_rank = Column(Integer, default=999999)
    volume_24h = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    settings = Column(JSON, nullable=True)  # Market-specific overrides

class Order(Base):
    __tablename__ = "orders"
    id = Column(String, primary_key=True)  # Exchange Order ID
    market_id = Column(String, ForeignKey("markets.id"), nullable=False, index=True)
    side = Column(String, nullable=False)  # BUY / SELL
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # OPEN, FILLED, CANCELED
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client_tag = Column(String, nullable=True)  # To track if it's a grid order

class Fill(Base):
    __tablename__ = "fills"
    id = Column(String, primary_key=True)  # Trade ID
    order_id = Column(String, ForeignKey("orders.id"), nullable=False, index=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False)
    side = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    size = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    timestamp = Column(DateTime(timezone=True), nullable=False)

class Lot(Base):
    """
    Tracks a complete trade cycle (Buy -> Sell).
    Defined in SPEC.md Section 5.4.
    """
    __tablename__ = "lots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String, ForeignKey("markets.id"), nullable=False, index=True)
    
    # Buy Side
    buy_order_id = Column(String, ForeignKey("orders.id"), nullable=False)
    buy_price = Column(Float, nullable=False)
    buy_size = Column(Float, nullable=False)
    buy_cost = Column(Float, nullable=False)  # Price * Size
    buy_time = Column(DateTime(timezone=True), server_default=func.now())

    # Sell Side
    sell_order_id = Column(String, ForeignKey("orders.id"), nullable=True)
    sell_price = Column(Float, nullable=True)
    exclude_from_pruning = Column(Boolean, default=False) # If manually pinned

    # State
    status = Column(String, default="OPEN")  # OPEN, CLOSED
    realized_pnl = Column(Float, default=0.0)

class BotState(Base):
    __tablename__ = "bot_state"
    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=False)
    # Example: key="BTC-USD_anchor", value={"price": 50000.0}

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    action = Column(String, nullable=False) # e.g. "START", "CONFIG_CHANGE"
    details = Column(JSON, nullable=True)

class DailySnapshot(Base):
    """
    Stores end-of-day PnL snapshots for historical tracking.
    Created automatically at end of each trading day.
    """
    __tablename__ = "daily_snapshots"
    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, unique=True, nullable=False, index=True)  # YYYY-MM-DD format
    realized_pnl = Column(Float, default=0.0)  # Total realized profit for this day
    trade_count = Column(Integer, default=0)   # Number of completed trades
    cumulative_pnl = Column(Float, default=0.0)  # Running total up to this day
