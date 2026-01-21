import logging
import uuid
import asyncio
from typing import List, Dict, Callable
from app.exchanges.interface import ExchangeAdapter
from app.db.models import Fill

logger = logging.getLogger(__name__)

class PaperWrapper(ExchangeAdapter):
    """
    Wraps a real adapter to intercept order placement.
    Uses real market data (get_ticker, get_products) but mocks execution.
    """
    def __init__(self, real_adapter: ExchangeAdapter):
        self.real = real_adapter
        self.open_orders = {} # id -> {price, size, side, market_id}
        self.fills = [] # List[Fill]

    async def get_products(self):
        return await self.real.get_products()

    async def get_ticker(self, product_id: str) -> float:
        return await self.real.get_ticker(product_id)

    async def get_balances(self) -> Dict[str, float]:
        # Return fake infinite balances so budget checks pass
        return {"USD": 100000.0, "BTC": 10.0, "ETH": 100.0}

    async def place_limit_order(self, product_id: str, side: str, price: float, size: float, post_only: bool = True) -> str:
        order_id = f"paper_{uuid.uuid4().hex[:8]}"
        logger.info(f"[PAPER] Placing {side} {size} @ {price} on {product_id} (ID: {order_id})")
        
        self.open_orders[order_id] = {
            "id": order_id,
            "product_id": product_id,
            "side": side,
            "price": price,
            "size": size,
            "status": "OPEN"
        }
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.open_orders:
            logger.info(f"[PAPER] Canceling {order_id}")
            del self.open_orders[order_id]
            return True
        logger.warning(f"[PAPER] Cancel failed, order not found: {order_id}")
        return False

    async def list_open_orders(self, product_id: str = None) -> List[Dict]:
        orders = []
        for oid, order in self.open_orders.items():
            if product_id and order["product_id"] != product_id:
                continue
            # Convert to Order model structure if needed, or expected dict
            # Interface says -> list[Order] usually, but let's check interface
            # For now returning the dicts we stored
            orders.append(order)
        return orders

    async def get_fills(self, since: float = None) -> List[Dict]:
        return [] # Fills are handled by simulate/check_fills for now

    async def stream_fills(self, callback: Callable):
        pass # No-op for paper mode, or could simulate

    async def stream_ticker(self, product_ids: List[str], callback: Callable):
        # Pass through to real adapter
        # But we might need to intercept to check fills if we don't do it in engine
        return await self.real.stream_ticker(product_ids, callback)

    # --- Simulation Logic ---
    def check_fills(self, market_id: str, current_price: float) -> List[dict]:
        """
        Check if any open paper orders matched the current price.
        Returns list of fill dicts.
        """
        filled_ids = []
        new_fills = []
        
        for oid, order in self.open_orders.items():
            if order["product_id"] != market_id:
                continue
                
            is_match = False
            if order["side"] == "BUY" and current_price <= order["price"]:
                is_match = True
            elif order["side"] == "SELL" and current_price >= order["price"]:
                is_match = True
                
            if is_match:
                logger.info(f"[PAPER] MATCH! {order['side']} {order['size']} @ {order['price']} (curr: {current_price})")
                filled_ids.append(oid)
                # Create fill data
                new_fills.append({
                    "order_id": oid,
                    "market_id": market_id,
                    "side": order["side"],
                    "price": order["price"], # Match at limit price
                    "size": order["size"],
                    "fee": 0.0
                })

        # Remove filled
        for oid in filled_ids:
            del self.open_orders[oid]
            
        return new_fills
