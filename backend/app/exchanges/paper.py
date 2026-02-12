import logging
import uuid
import asyncio
from typing import List, Dict, Callable
from app.exchanges.interface import ExchangeAdapter

logger = logging.getLogger(__name__)

class PaperWrapper(ExchangeAdapter):
    """
    Wraps a real adapter to intercept order placement.
    Uses real market data (get_ticker, get_products) but mocks execution.
    
    IMPORTANT: This is stateless - check_fills queries the database directly.
    """
    def __init__(self, real_adapter: ExchangeAdapter, session_factory=None):
        self.real = real_adapter
        self.session_factory = session_factory
        # In-memory cache for quick lookups (also kept in sync with DB)
        self.order_cache = {}

    async def get_products(self):
        return await self.real.get_products()

    async def get_ticker(self, product_id: str) -> float:
        return await self.real.get_ticker(product_id)

    async def stream_ticker(self, product_ids, callback):
        return await self.real.stream_ticker(product_ids, callback)

    async def get_product_candles(self, *args, **kwargs):
        """Delegate candle fetching to the real adapter for catch-up mechanism."""
        return await self.real.get_product_candles(*args, **kwargs)

    async def get_balances(self) -> Dict[str, float]:
        # Return fake infinite balances so budget checks pass
        return {"USD": 100000.0, "BTC": 10.0, "ETH": 100.0}

    async def place_limit_order(self, product_id: str, side: str, price: float, size: float, post_only: bool = True) -> str:
        import time
        order_id = f"paper_{int(time.time()*1000)}_{uuid.uuid4().hex}"
        logger.info(f"[PAPER] Placing {side} {size} @ {price} on {product_id} (ID: {order_id})")
        
        # Cache for immediate inspection
        self.order_cache[order_id] = {
            "id": order_id,
            "product_id": product_id,
            "side": side,
            "price": price,
            "size": size,
            "status": "OPEN"
        }
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        # Remove from cache if present
        if order_id in self.order_cache:
            logger.info(f"[PAPER] Canceling {order_id}")
            del self.order_cache[order_id]
            return True
        # For orders not in cache (e.g., from DB after restart), still return True
        # The database update is handled by engine.py
        logger.info(f"[PAPER] Cancel request for {order_id} (not in cache, likely from DB)")
        return True

    async def list_open_orders(self, product_id: str = None) -> List[Dict]:
        return [o for o in self.order_cache.values() 
                if product_id is None or o["product_id"] == product_id]

    async def get_fills(self, since: float = None) -> List[Dict]:
        return []

    async def stream_fills(self, callback):
        pass

    async def stream_ticker(self, product_ids: List[str], callback):
        pass

    # --- Simulation Logic ---
    def check_fills(self, market_id: str, current_price: float, db_orders: List = None) -> List[dict]:
        """
        Check if any open paper orders matched the current price.
        
        Args:
            market_id: The market to check
            current_price: Current market price
            db_orders: List of Order objects from database (injected by engine)
        
        Returns list of fill dicts.
        """
        filled_ids = []
        new_fills = []
        
        # Use database orders if provided, otherwise fall back to cache
        orders_to_check = []
        
        if db_orders is not None:
            # Use orders from database (most reliable)
            for order in db_orders:
                if order.status == "OPEN":
                    orders_to_check.append({
                        "id": order.id,
                        "product_id": order.market_id,
                        "side": order.side,
                        "price": order.price,
                        "size": order.size
                    })
        else:
            # Fallback to cache
            orders_to_check = [o for o in self.order_cache.values() 
                              if o["product_id"] == market_id]
        
        for order in orders_to_check:
            if order["product_id"] != market_id:
                continue
                
            is_match = False
            if order["side"] == "BUY" and current_price <= order["price"]:
                is_match = True
            elif order["side"] == "SELL" and current_price >= order["price"]:
                is_match = True
                
            if is_match:
                logger.info(f"[PAPER] MATCH! {order['side']} {order['size']} @ {order['price']} (curr: {current_price})")
                filled_ids.append(order["id"])
                # Create fill data
                new_fills.append({
                    "order_id": order["id"],
                    "market_id": market_id,
                    "side": order["side"],
                    "price": order["price"],  # Match at limit price
                    "size": order["size"],
                    "fee": 0.0
                })

        # Remove filled orders from cache
        for oid in filled_ids:
            if oid in self.order_cache:
                del self.order_cache[oid]
            
        return new_fills
