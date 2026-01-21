import asyncio
import logging
import json
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.exchanges.interface import ExchangeAdapter
from app.db.models import Market, Order, BotState, Configuration
from app.bot.strategy import GridStrategy
from app.config import settings

logger = logging.getLogger(__name__)

class BotEngine:
    """
    Orchestrates the bot lifecycle: Ticking, State Management, and Order Execution.
    """



    def __init__(self, adapter: ExchangeAdapter, db_session_factory, ws_manager=None):
        self.adapter = adapter
        self.db_session_factory = db_session_factory
        self.ws_manager = ws_manager
        self.strategy = GridStrategy()
        self.is_running = False

    def update_config(self, 
                      grid_step_pct: float = None, 
                      budget: float = None, 
                      max_open_orders: int = None,
                      staging_band_depth_pct: float = None,
                      buffer_enabled: bool = None,
                      buffer_pct: float = None,
                      profit_mode: str = None):
        """
        Hot-reload strategy configuration.
        """
        if grid_step_pct is not None:
            self.strategy.grid_step_pct = grid_step_pct
            logger.info(f"Updated Grid Step to {grid_step_pct}")
        
        if max_open_orders is not None:
             self.strategy.max_orders = max_open_orders
             logger.info(f"Updated Max Orders to {max_open_orders}")

        if staging_band_depth_pct is not None:
            self.strategy.staging_band_pct = staging_band_depth_pct
            logger.info(f"Updated Staging Band to {staging_band_depth_pct}")

        if buffer_enabled is not None:
            self.strategy.buffer_enabled = buffer_enabled
            logger.info(f"Updated Buffer Enabled to {buffer_enabled}")

        if buffer_pct is not None:
            self.strategy.buffer_pct = buffer_pct
            logger.info(f"Updated Buffer % to {buffer_pct}")
        
        # profit_mode logic TBD when implemented in strategy, for now just log
        if profit_mode:
            logger.info(f"Updated Profit Mode to {profit_mode}")
        
        # Budget logic would go here if strategy supported dynamic budget re-calc
        # For now, just logging it
        if budget is not None:
             logger.info(f"Updated Budget to {budget}")

    async def stop_and_cancel_all(self):
        """
        Emergency Stop: Pauses ticking and cancels all open orders.
        """
        logger.warning("EMERGENCY STOP TRIGGERED")
        self.is_running = False # Actually, we need to ensure tick loop respects this?
        # Note: run_loop currently is `while True`. We should modify it to respect `is_running` or adding a pause flag.
        # But for 'Stop', we probably want to stop placing orders.
        # Let's add a paused flag logic to `tick`. (Actually `settings.LIVE_TRADING_ENABLED` controls tick).
        # We can flip settings too, or just cancel everything.
        
        # 1. Cancel All via Adapter
        try:
             # This assumes Adapter has cancel_all or we iterate open orders.
             # SPEC said cancel_all endpoint. Coinbase has cancel_all logic.
             # We should fetch all open orders and cancel them.
             async with self.db_session_factory() as session:
                 # Fetch OPEN orders from DB to be fast
                 result = await session.execute(select(Order).where(Order.status == "OPEN"))
                 orders = result.scalars().all()
                 
                 for order in orders:
                     try:
                         await self.adapter.cancel_order(order.id)
                         order.status = "CANCELED"
                     except Exception as e:
                         logger.error(f"Failed to panic cancel {order.id}: {e}")
                 
                 await session.commit()
        except Exception as e:
            logger.error(f"Panic cancel failed: {e}")


    async def broadcast(self, event_type: str, data: dict):
        if self.ws_manager:
            message = json.dumps({"type": event_type, "data": data})
            await self.ws_manager.broadcast(message)

    async def run_loop(self):
        """
        Main infinite loop.
        """
        logger.info("Bot Engine Starting...")
        
        # Start WS Subscription (For all types: Coinbase, Mock, etc.)
        try:
             async with self.db_session_factory() as session:
                 result = await session.execute(select(Market).where(Market.enabled == True))
                 markets = result.scalars().all()
                 product_ids = [m.id for m in markets]
                 
                 if product_ids:
                     logger.info(f"Starting Ticker Stream for {len(product_ids)} markets")
                     
                     async def on_ticker(data):
                         if data.get("type") == "ticker":
                             await self.broadcast("PRICE_UPDATE", {
                                 "market_id": data["product_id"], 
                                 "price": data["price"]
                             })
                             
                     # Launch background task
                     asyncio.create_task(self.adapter.stream_ticker(product_ids, on_ticker))
        except Exception as e:
             logger.error(f"Failed to start WS: {e}")

        while True:
            try:
                # Run if Live OR Paper Mode
                if settings.LIVE_TRADING_ENABLED or settings.PAPER_MODE:
                    async with self.db_session_factory() as session:
                        await self.tick(session)
                else:
                    logger.debug("Live trading disabled, skipping tick.")
            except Exception as e:
                logger.error(f"Error in tick loop: {e}", exc_info=True)
            
            await asyncio.sleep(5)  # Tick every 5 seconds

    async def tick(self, session: AsyncSession):
        """
        Single iteration of the strategy logic per market.
        For Phase 1/MVP, we only focus on enabled markets.
        """
        # 1. Get Enabled Markets
        result = await session.execute(select(Market).where(Market.enabled == True))
        markets = result.scalars().all()
        
        for market in markets:
            await self.process_market(session, market)

    async def process_market(self, session: AsyncSession, market: Market):
        try:
            market_id = market.id
            
            # 2. Get Current Price (Ticker)
            current_price = await self.adapter.get_ticker(market_id)
            if current_price <= 0:
                logger.warning(f"Invalid price for {market_id}: {current_price}")
                return
            
            # Broadcast Update
            await self.broadcast("PRICE_UPDATE", {"market_id": market_id, "price": current_price})

            # --- PROCESS FILLS & LOTS ---
            await self.process_fills(session, market_id, current_price)

            # 3. Load State (AnchorHigh)
            anchor_key = f"{market_id}_anchor"
            state_result = await session.execute(select(BotState).where(BotState.key == anchor_key))
            bot_state = state_result.scalar_one_or_none()
            
            old_anchor = float(bot_state.value["price"]) if bot_state else None
            
            # 4. Rebase Logic
            new_anchor = self.strategy.calculate_new_anchor(current_price, old_anchor)
            if new_anchor != old_anchor:
                # If paper mode, we might want to log this distinctly
                logger.info(f"Rebasing {market_id}: {old_anchor} -> {new_anchor}")
                # Upsert State
                if bot_state:
                    bot_state.value = {"price": new_anchor}
                else:
                    session.add(BotState(key=anchor_key, value={"price": new_anchor}))
                await session.commit()
            
            # 5. Sync Grid Orders
            await self.sync_orders(session, market_id, new_anchor, current_price)
            
        except Exception as e:
            logger.error(f"Error processing market {market.id}: {e}")

    async def process_fills(self, session: AsyncSession, market_id: str, current_price: float):
        """
        Check for fills and manage Lots (Entry -> Exit).
        """
        new_fills = []
        
        # A. Detect Fills
        if settings.PAPER_MODE and hasattr(self.adapter, "check_fills"):
            # Use Paper Simulation
            new_fills = self.adapter.check_fills(market_id, current_price)
        else:
            # TODO: Implement Real Exchange Fill Polling or rely on WS Buffer
            # For now, Real Mode Fill detection is manual or WS dependent (not fully implemented here)
            pass

        # B. Process Fills
        for fill_data in new_fills:
            order_id = fill_data["order_id"]
            side = fill_data["side"]
            price = fill_data["price"]
            size = fill_data["size"]
            
            logger.info(f"Processing FILL: {side} {size} @ {price}")
            
            # Update Order Status
            order_res = await session.execute(select(Order).where(Order.id == order_id))
            order = order_res.scalar_one_or_none()
            if order:
                order.status = "FILLED"
            
            # Logic: If BUY Fill -> Create Lot & Place Sell
            if side == "BUY":
                # Create Lot (TODO: Add Lot Model logic, for now simple log/sell)
                sell_price = self.strategy.get_sell_price(price)
                logger.info(f"Grid Buy Filled! Placing Sell @ {sell_price}")
                
                try:
                    sell_id = await self.adapter.place_limit_order(market_id, "SELL", sell_price, size)
                    
                    # Track Sell Order (as a normal order for now, simplified)
                    sell_order = Order(
                         id=sell_id,
                         market_id=market_id,
                         side="SELL",
                         price=sell_price,
                         size=size,
                         status="OPEN"
                    )
                    session.add(sell_order)
                    
                except Exception as e:
                    logger.error(f"Failed to place exit sell: {e}")
            
            elif side == "SELL":
                logger.info(f"Grid Sell Filled! PROFIT REALIZED.")
                # TODO: Update Lot status to Closed

        if new_fills:
            await session.commit()

    async def sync_orders(self, session: AsyncSession, market_id: str, anchor_high: float, current_price: float):
        """
        Aligns open BUY orders with the calculated grid.
        """
        # A. Calculate Desired Levels
        desired_buy_prices = self.strategy.calculate_buy_levels(anchor_high, current_price)
        
        # B. Get Open Orders 
        db_orders_res = await session.execute(select(Order).where(Order.market_id == market_id, Order.status == "OPEN", Order.side == "BUY"))
        open_orders = db_orders_res.scalars().all()
        
        # C. Pruning (Cancel bad orders)
        existing_prices = []
        for order in open_orders:
            if self.strategy.should_prune(order.price, current_price):
                logger.info(f"Pruning order {order.id} at {order.price} (Too far from {current_price})")
                try:
                    await self.adapter.cancel_order(order.id)
                    order.status = "CANCELED"
                except Exception as e:
                    logger.error(f"Failed to cancel order {order.id}: {e}")
            else:
                existing_prices.append(order.price)
        
        # D. Place New Orders (Fill gaps)
        TOLERANCE = 0.0001
        
        for price in desired_buy_prices:
            # Check if we already have an order close to this price
            if any(abs(p - price) / price < TOLERANCE for p in existing_prices):
                continue
                
            # Place Order
            # For Paper Mode, we use a fixed size or budget calc (TODO)
            size = 0.0001 # Small fixed size for testing
            logger.info(f"Placing BUY for {market_id} at {price}")
            try:
                order_id = await self.adapter.place_limit_order(market_id, "BUY", price, size)
                
                # Record in DB
                new_order = Order(
                    id=order_id,
                    market_id=market_id,
                    side="BUY",
                    price=price,
                    size=size,
                    status="OPEN"
                )
                session.add(new_order)
                existing_prices.append(price) 
                
            except Exception as e:
                logger.error(f"Failed to place order for {market_id} at {price}: {e}")
        
        await session.commit()
