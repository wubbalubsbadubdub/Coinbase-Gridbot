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

        # if profit_mode: ... (Removed invalid block)
        pass # Strategy initialized above

    # Wait, I need to update the signature of update_config first.
    # Let me do that in the "ReplacementContent" properly.
    
    def update_config(self, 
                      grid_step_pct: float = None, 
                      budget: float = None, 
                      max_open_orders: int = None,
                      staging_band_depth_pct: float = None,
                      buffer_enabled: bool = None,
                      buffer_pct: float = None,
                      profit_mode: str = None,
                      custom_profit_pct: float = None,
                      monthly_profit_target_usd: float = None):
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
        
        if profit_mode:
            self.strategy.profit_mode = profit_mode
            logger.info(f"Updated Profit Mode to {profit_mode}")

        if custom_profit_pct is not None:
            self.strategy.custom_profit_pct = custom_profit_pct
            logger.info(f"Updated Custom Profit % to {custom_profit_pct}")
            
        if monthly_profit_target_usd is not None:
            self.strategy.monthly_profit_target_usd = monthly_profit_target_usd
            logger.info(f"Updated Monthly Target to {monthly_profit_target_usd}")
        
        # Budget logic 
        if budget is not None:
             self.strategy.budget = budget
             logger.info(f"Updated Budget to {budget}")

    async def check_monthly_reset(self, session: AsyncSession):
        """
        Resets profit counter if month changed.
        """
        import datetime
        current_month = datetime.datetime.now().month
        
        key = "profit_tracker"
        res = await session.execute(select(BotState).where(BotState.key == key))
        state = res.scalar_one_or_none()
        
        if not state:
            # Init
            session.add(BotState(key=key, value={"current_month_profit_usd": 0.0, "last_profit_reset_month": current_month}))
            await session.commit()
            return

        data = state.value
        last_month = data.get("last_profit_reset_month", -1)
        
        if current_month != last_month:
            logger.info(f"New Month detected ({current_month}). Resetting Profit Counter.")
            state.value = {"current_month_profit_usd": 0.0, "last_profit_reset_month": current_month}
            await session.commit()

    async def add_profit(self, session: AsyncSession, amount_usd: float):
        key = "profit_tracker"
        res = await session.execute(select(BotState).where(BotState.key == key))
        state = res.scalar_one_or_none()
        if state:
            # Creating a new dict to ensure SQLAlchemy detects change for JSON
            current_data = dict(state.value)
            old_profit = current_data.get("current_month_profit_usd", 0.0)
            new_profit = old_profit + amount_usd
            current_data["current_month_profit_usd"] = new_profit
            state.value = current_data
            logger.info(f"Profit Recorded: +${amount_usd:.2f} | Month Total: ${new_profit:.2f}")

    async def get_current_monthly_profit(self, session: AsyncSession) -> float:
        key = "profit_tracker"
        res = await session.execute(select(BotState).where(BotState.key == key))
        state = res.scalar_one_or_none()
        if state:
             return state.value.get("current_month_profit_usd", 0.0)
        return 0.0

    async def stop_and_cancel_all(self):
        """
        Emergency Stop: Pauses ticking, disables all markets, and cancels all open orders.
        """
        logger.warning("EMERGENCY STOP TRIGGERED")
        self.is_running = False
        
        try:
            async with self.db_session_factory() as session:
                # 1. Disable ALL enabled markets so bot doesn't recreate orders
                await session.execute(
                    update(Market)
                    .where(Market.enabled == True)
                    .values(enabled=False)
                )
                
                # 2. Cancel all open orders
                result = await session.execute(select(Order).where(Order.status == "OPEN"))
                orders = result.scalars().all()
                
                for order in orders:
                    try:
                        await self.adapter.cancel_order(order.id)
                        order.status = "CANCELED"
                    except Exception as e:
                        logger.error(f"Failed to panic cancel {order.id}: {e}")
                
                await session.commit()
                logger.info(f"Emergency stop: Disabled all markets and canceled {len(orders)} orders")
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
            
            # --- PROFIT TRACKING & RESET ---
            await self.check_monthly_reset(session)
            
            # 2. Get Current Price (Ticker)
            current_price = await self.adapter.get_ticker(market_id)
            if current_price <= 0:
                logger.warning(f"Invalid price for {market_id}: {current_price}")
                return
            
            # Broadcast Update - MOVED to after Rebase
            # await self.broadcast("PRICE_UPDATE", {"market_id": market_id, "price": current_price})

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
            
            # Broadcast Update (Now with latest Anchor)
            grid_top = new_anchor
            if self.strategy.buffer_enabled and self.strategy.buffer_pct > 0:
                grid_top = new_anchor * (1 - self.strategy.buffer_pct)

            await self.broadcast("PRICE_UPDATE", {
                "market_id": market_id, 
                "price": current_price,
                "anchor": new_anchor,
                "grid_top": grid_top
            })
            
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
                # Realized Profit Calculation
                # For now, approximate as (Price - (Price / (1+Step))) * Size? 
                # Or just (Price * Size) - Buy_Cost. 
                # Since we don't track Buy Cost perfectly in Order yet, let's use Strategy Estimate:
                # Profit ~= Size * BuyPrice * StepPct 
                # BuyPrice ~= SellPrice / (1 + Step)
                # Profit = Size * (SellPrice / (1+Step)) * Step
                step = self.strategy.grid_step_pct
                estimated_profit = size * (price / (1 + step)) * step
                
                logger.info(f"Grid Sell Filled! PROFIT REALIZED: ${estimated_profit:.2f}")
                await self.add_profit(session, estimated_profit)
                
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
            # Dynamic Sizing Logic
            base_size = 0.0001 # Default fixed
            
            mode = self.strategy.profit_mode
            current_profit = await self.get_current_monthly_profit(session)
            target = self.strategy.monthly_profit_target_usd
            
            # Logic
            if mode == "SMART_REINVEST":
                if current_profit >= target:
                    # Compound! (Increase size)
                    # Example: Double size or proportional? 
                    # Let's say: base_size * (1 + (profit - target)/target) ? 
                    # For MVP, let's just DOUBLE it to prove it works
                    base_size = 0.0002 
                    logger.info(f"Smart Reinvest Active! (Profit ${current_profit:.2f} >= ${target}). Boosting Size.")
                else:
                    logger.info(f"Smart Reinvest: Building Base (Profit ${current_profit:.2f} < ${target}). Standard Size.")
            
            elif mode == "STEP_REINVEST":
                 # Always boost
                 base_size = 0.0002
            
            size = base_size
            
            logger.info(f"Placing BUY for {market_id} at {price} (Size: {size})")
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
