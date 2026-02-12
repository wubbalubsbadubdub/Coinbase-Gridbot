import asyncio
import logging
import json
import time
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.exchanges.interface import ExchangeAdapter
from app.db.models import Market, Order, BotState, Configuration, Lot, Fill
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
        self.order_cache = {} # In-Memory Cache: {order_id: {data}}

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
                      monthly_profit_target_usd: float = None,
                      sizing_mode: str = None,
                      fixed_usd_per_trade: float = None,
                      capital_pct_per_trade: float = None):
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
        
        # NEW: Trade sizing options
        if sizing_mode is not None:
            self.strategy.sizing_mode = sizing_mode
            logger.info(f"Updated Sizing Mode to {sizing_mode}")
        
        if fixed_usd_per_trade is not None:
            self.strategy.fixed_usd_per_trade = fixed_usd_per_trade
            logger.info(f"Updated Fixed USD per Trade to {fixed_usd_per_trade}")
        
        if capital_pct_per_trade is not None:
            self.strategy.capital_pct_per_trade = capital_pct_per_trade
            logger.info(f"Updated Capital % per Trade to {capital_pct_per_trade}")

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
                             market_id = data["product_id"]
                             price = float(data["price"])
                             
                             await self.broadcast("PRICE_UPDATE", {
                                 "market_id": market_id, 
                                 "price": price
                             })
                             
                             # Real-time Paper Fill Execution (Hybrid Mode)
                             if settings.PAPER_MODE:
                                 # 1. Fast Cache Check (No DB)
                                 should_process = False
                                 for oid, order_data in self.order_cache.items():
                                     if order_data['market_id'] == market_id and order_data['status'] == "OPEN":
                                         # Check if price moved through order
                                         if order_data['side'] == "BUY" and price <= order_data['price']:
                                             should_process = True
                                             break
                                         elif order_data['side'] == "SELL" and price >= order_data['price']:
                                             should_process = True
                                             break
                                 
                                 if should_process:
                                     try:
                                         async with self.db_session_factory() as session:
                                             await self.process_fills(session, market_id, price)
                                     except Exception as e:
                                         logger.error(f"RT Fill Error: {e}")

                             
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
            
            # Catch-up Mechanism: Check candles every ~60s
            # (Simple modulo check or secondary loop - keep it simple here)
            if int(time.time()) % 60 < 5: # roughly every minute
                 if settings.PAPER_MODE:
                     async with self.db_session_factory() as session:
                         # Get all enabled markets
                         result = await session.execute(select(Market).where(Market.enabled == True))
                         markets = result.scalars().all()
                         for market in markets:
                             await self.check_missed_candles(session, market.id)

    async def check_missed_candles(self, session: AsyncSession, market_id: str):
        """
        Safety Net: Checks last 5 minutes of candles to see if we missed a wick.
        """
        try:
            # 1. Get recent candles (last 5 mins)
            end_time = int(time.time())
            start_time = end_time - 300 # 5 mins ago
            
            # Need to implement get_product_candles in adapter first (Done)
            if not hasattr(self.adapter, "get_product_candles"):
                return
                
            # Coinbase Advanced Trade uses "ONE_MINUTE", not "60"
            granularity = "ONE_MINUTE" if settings.EXCHANGE_TYPE == "coinbase" else "60"
            candles = await self.adapter.get_product_candles(market_id, start_time, end_time, granularity)
            
            if not candles:
                return

            # 2. Check overlap with Open Orders in Cache
            # (We use cache because it's up to date)
            relevant_orders = [o for o in self.order_cache.values() if o['market_id'] == market_id and o['status'] == 'OPEN']
            
            if not relevant_orders:
                return
                
            fills_triggered = False
            
            for candle in candles:
                # Candle format: [timestamp, low, high, open, close, vol] - Verify format!
                # Coinbase V3: object dict? Or array?
                # Adapter returns "candles" list. Docs say objects.
                # Let's assume dict based on typical JSON response, but check adapter.
                # Adapter returns data.get("candles", []).
                # Each candle is a dict like {'start':..., 'low':..., 'high':...}
                
                low = float(candle.get('low', 0))
                high = float(candle.get('high', 0))
                
                if low == 0 or high == 0: 
                    continue
                    
                for order in relevant_orders:
                    if order['side'] == "BUY" and low <= order['price']:
                         # HIT!
                         logger.warning(f"Catch-up: Found missed BUY match for {market_id} @ {low} (Order: {order['price']})")
                         await self.process_fills(session, market_id, low) # Use low as price to guarantee fill
                         fills_triggered = True
                         
                    elif order['side'] == "SELL" and high >= order['price']:
                         # HIT!
                         logger.warning(f"Catch-up: Found missed SELL match for {market_id} @ {high} (Order: {order['price']})")
                         await self.process_fills(session, market_id, high)
                         fills_triggered = True
            
            if fills_triggered:
                # process_fills handles commit
                pass
                
        except Exception as e:
            logger.error(f"Error in Catch-up mechanism: {e}")

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
        

        # B. Process Fills
        # HYBRID ENGINE: Use Cache for fast matching, fallback to DB if needed
        
        # 1. Update Cache from DB (if cache empty/stale, usually sync_orders handles this)
        # But we rely on sync_orders to populate cache.
        
        if settings.PAPER_MODE and hasattr(self.adapter, "check_fills"):
             # FAST PATH: Check against In-Memory Cache
             # Convert cache dicts to objects expected by check_fills if needed
             # or just reimplement check_fills logic here for speed?
             # check_fills expects list of objects with .id, .price, .side
             
             # Let's create lightweight objects from cache
             class FastOrder:
                 def __init__(self, d):
                     self.id = d['id']
                     self.market_id = d['market_id']
                     self.side = d['side']
                     self.price = d['price']
                     self.size = d['size']
                     self.status = d['status']

             limit_orders = [FastOrder(d) for d in self.order_cache.values() if d['market_id'] == market_id and d['status'] == 'OPEN']
             
             # Detect Fills
             new_fills = self.adapter.check_fills(market_id, current_price, db_orders=limit_orders)
        else:
             # Real Mode - Manual/WS
             pass

        # C. Apply Fills
        for fill_data in new_fills:
            order_id = fill_data["order_id"]
            
            # Update Cache IMMEDIATELY
            if order_id in self.order_cache:
                del self.order_cache[order_id]
            side = fill_data["side"]
            price = fill_data["price"]
            size = fill_data["size"]
            
            logger.info(f"Processing FILL: {side} {size} @ {price}")
            
            # Create Fill record for history
            from datetime import datetime, timezone
            import uuid
            fill = Fill(
                id=f"fill_{uuid.uuid4().hex[:8]}",
                order_id=order_id,
                market_id=market_id,
                side=side,
                price=price,
                size=size,
                fee=fill_data.get("fee", 0.0),
                timestamp=datetime.now(timezone.utc)
            )
            session.add(fill)
            logger.info(f"Recorded fill in history: {side} {size} @ {price}")
            
            # Update Order Status
            order_res = await session.execute(select(Order).where(Order.id == order_id))
            order = order_res.scalar_one_or_none()
            if order:
                order.status = "FILLED"
            
            # Logic: If BUY Fill -> Create Lot & Place Sell
            if side == "BUY":
                sell_price = self.strategy.get_sell_price(price)
                logger.info(f"Grid Buy Filled! Placing Sell @ {sell_price}")
                
                try:
                    sell_id = await self.adapter.place_limit_order(market_id, "SELL", sell_price, size)
                    
                    # Track Sell Order
                    sell_order = Order(
                         id=sell_id,
                         market_id=market_id,
                         side="SELL",
                         price=sell_price,
                         size=size,
                         status="OPEN"
                    )
                    session.add(sell_order)
                    
                    # Create Lot to track this trade cycle
                    lot = Lot(
                        market_id=market_id,
                        buy_order_id=order_id,
                        buy_price=price,
                        buy_size=size,
                        buy_cost=price * size,
                        sell_order_id=sell_id,
                        sell_price=sell_price,
                        status="OPEN"
                    )
                    session.add(lot)
                    logger.info(f"Created Lot: Buy @ {price} -> Sell @ {sell_price}")
                    
                except Exception as e:
                    logger.error(f"Failed to place exit sell: {e}")
            
            elif side == "SELL":
                # Find and close the associated Lot
                lot_res = await session.execute(
                    select(Lot).where(Lot.sell_order_id == order_id)
                )
                lot = lot_res.scalar_one_or_none()
                
                if lot:
                    # Calculate actual profit
                    sell_proceeds = price * size
                    profit = sell_proceeds - lot.buy_cost
                    lot.status = "CLOSED"
                    lot.realized_pnl = profit
                    logger.info(f"Grid Sell Filled! Lot #{lot.id} CLOSED. Profit: ${profit:.2f}")
                    await self.add_profit(session, profit)
                else:
                    # Fallback: estimate profit if lot not found (shouldn't happen)
                    step = self.strategy.grid_step_pct
                    estimated_profit = size * (price / (1 + step)) * step
                    logger.warning(f"Lot not found for sell order {order_id}. Estimated profit: ${estimated_profit:.2f}")
                    await self.add_profit(session, estimated_profit)

        if new_fills:
            await session.commit()

    async def sync_orders(self, session: AsyncSession, market_id: str, anchor_high: float, current_price: float):
        """
        Aligns open BUY orders with the calculated grid.
        CRITICAL: Only place BUY at a level if there's no open order AND no open Lot at that level.
        """
        # A. Calculate Desired Levels
        desired_buy_prices = self.strategy.calculate_buy_levels(anchor_high, current_price)
        
        # B. Get Open BUY Orders 
        db_orders_res = await session.execute(select(Order).where(Order.market_id == market_id, Order.status == "OPEN", Order.side == "BUY"))
        open_orders = db_orders_res.scalars().all()

        # SYNC CACHE: Update in-memory cache with latest DB state
        # We only cache BUY orders here? No, process_fills needs SELL too.
        # sync_orders only manages BUYs. logic flow:
        # 1. process_fills logic handles SELLS (which are created immediately upon fill)
        # So we should ensure ALL open orders for this market are in cache.
        # Let's quickly fetch ALL open orders to sync cache fully
        all_orders_res = await session.execute(select(Order).where(Order.market_id == market_id, Order.status == "OPEN"))
        all_orders = all_orders_res.scalars().all()
        
        # Rebuild cache for this market to be safe
        # (Remove old market entries first? Or just update?)
        # For safety/simplicity: properties update.
        for o in all_orders:
            self.order_cache[o.id] = {
                'id': o.id, 'market_id': o.market_id, 'side': o.side,
                'price': o.price, 'size': o.size, 'status': o.status
            }
        
        # Now use open_orders (BUYs) for grid logic

        
        # B2. Get Open Lots (BUYs that filled but SELL not yet complete) - CRITICAL FIX
        open_lots_res = await session.execute(select(Lot).where(Lot.market_id == market_id, Lot.status == "OPEN"))
        open_lots = open_lots_res.scalars().all()
        
        # C. Strict Synchronization (Prune anything that isn't a valid level)
        grid_step = self.strategy.grid_step_pct
        if grid_step <= 0:
             grid_step = 0.01 
        TOLERANCE = grid_step * 0.2
        
        # Track which desired levels are already covered by an existing order
        # Key: index in desired_buy_prices
        covered_indices = set()
        
        for order in open_orders:
            # Check if this order matches ANY desired level
            match_index = -1
            for i, price in enumerate(desired_buy_prices):
                if abs(order.price - price) / price < TOLERANCE:
                    match_index = i
                    break
            
            # Pruning Logic:
            # 1. If it's outside the staging band (strategy.should_prune) OR
            # 2. If it doesn't match a valid grid level (Ghost Order)
            is_valid_level = (match_index != -1)
            is_in_band = not self.strategy.should_prune(order.price, current_price)
            
            if is_valid_level and is_in_band:
                # Keep it
                covered_indices.add(match_index)
            else:
                # Prune it
                reason = "Ghost Order (Settings Changed)" if not is_valid_level else "Out of Band"
                logger.info(f"Pruning order {order.id} @ {order.price} ({reason})")
                try:
                    await self.adapter.cancel_order(order.id)
                    order.status = "CANCELED"
                    if order.id in self.order_cache:
                        del self.order_cache[order.id]
                except Exception as e:
                    logger.error(f"Failed to cancel order {order.id}: {e}")

        # C2. Also block levels where we have open Lots (buy filled, waiting for sell)
        for lot in open_lots:
             for i, price in enumerate(desired_buy_prices):
                if abs(lot.buy_price - price) / price < TOLERANCE:
                    covered_indices.add(i)
                    break
        
        # D. Place New Orders (Fill gaps)
        for i, price in enumerate(desired_buy_prices):
            if i in covered_indices:
                continue
            
            # Place Order
            # Dynamic Sizing Logic - 3 modes
            sizing_mode = getattr(self.strategy, 'sizing_mode', 'BUDGET_SPLIT')
            base_budget = getattr(self.strategy, 'budget', 1000.0)
            
            # --- SMART REINVEST LOGIC ---
            # 1. Get current profit
            current_profit = await self.get_current_monthly_profit(session)
            # 2. Calculate Effective Budget
            effective_budget = self.strategy.get_effective_budget(current_profit)
            
            if effective_budget != base_budget:
                logger.info(f"Smart Reinvest Active: Budget ${base_budget:.2f} -> ${effective_budget:.2f} (Profit: ${current_profit:.2f})")
            
            max_orders = getattr(self.strategy, 'max_orders', 10)
            fixed_usd = getattr(self.strategy, 'fixed_usd_per_trade', 10.0)
            capital_pct = getattr(self.strategy, 'capital_pct_per_trade', 1.0)
            
            if sizing_mode == "BUDGET_SPLIT":
                # Mode 1: Divide budget evenly across max orders
                # Size = (Effective Budget / Max Orders) / Price
                usd_per_order = effective_budget / max(max_orders, 1)
                size = usd_per_order / price
                logger.debug(f"BUDGET_SPLIT: ${usd_per_order:.2f}/order (Budget: ${effective_budget:.2f}) → {size:.8f} @ ${price:.2f}")
            
            elif sizing_mode == "FIXED_USD":
                # Mode 2: Fixed USD amount per trade
                # Size = Fixed USD / Price
                # (Smart Reinvest doesn't affect FIXED_USD mode unless we change the fixed amount logic, 
                # but usually reinvestment implies sizing up relative to capital. 
                # For now, we only apply it to budget-based modes as per typical grid logic).
                size = fixed_usd / price
                logger.debug(f"FIXED_USD: ${fixed_usd:.2f} → {size:.8f} @ ${price:.2f}")
            
            elif sizing_mode == "CAPITAL_PCT":
                # Mode 3: Percentage of available capital per trade
                # Available = Effective Budget
                available_capital = effective_budget 
                usd_per_order = available_capital * (capital_pct / 100.0)
                size = usd_per_order / price
                logger.debug(f"CAPITAL_PCT: {capital_pct}% of ${available_capital:.2f} = ${usd_per_order:.2f} → {size:.8f}")
            
            else:
                # Fallback to old default
                size = 0.0001
                logger.warning(f"Unknown sizing_mode '{sizing_mode}', using default 0.0001")
            
            # Ensure minimum size (Coinbase BTC minimum is ~0.0001)
            min_size = 0.00001
            size = max(round(size, 8), min_size)
            
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

                
                # Add to Cache
                self.order_cache[order_id] = {
                     'id': order_id, 'market_id': market_id, 'side': "BUY",
                     'price': price, 'size': size, 'status': "OPEN"
                }
                
            except Exception as e:
                logger.error(f"Failed to place order for {market_id} at {price}: {e}")
        
        await session.commit()
