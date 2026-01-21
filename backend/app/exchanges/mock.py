from typing import List, Dict, Any, Optional
import asyncio
import uuid
import time
from app.exchanges.interface import ExchangeAdapter
from app.db.models import Order  # Using DB model structure for return types where appropriate

class MockAdapter(ExchangeAdapter):
    """
    In-memory mock exchange for testing and paper trading.
    """
    def __init__(self):
        self.orders: Dict[str, Dict[str, Any]] = {}  # order_id -> order_data
        self.balances = {"USD": 10000.0, "BTC": 1.0, "ETH": 10.0}
        self.current_prices = {
            "BTC-USD": 50000.0, 
            "ETH-USD": 3000.0,
            "SOL-USD": 100.0,
            "ADA-USD": 1.20,
            "DOT-USD": 7.50
        }

    async def get_products(self) -> List[Any]:
        return [
            {"id": "BTC-USD", "base_currency": "BTC", "quote_currency": "USD"},
            {"id": "ETH-USD", "base_currency": "ETH", "quote_currency": "USD"},
            {"id": "SOL-USD", "base_currency": "SOL", "quote_currency": "USD"},
            {"id": "ADA-USD", "base_currency": "ADA", "quote_currency": "USD"},
            {"id": "DOT-USD", "base_currency": "DOT", "quote_currency": "USD"}
        ]

    async def get_balances(self) -> Dict[str, float]:
        return self.balances

    async def get_ticker(self, product_id: str) -> float:
        return self.current_prices.get(product_id, 0.0)

    async def place_limit_order(self, product_id: str, side: str, price: float, size: float, post_only: bool = True) -> str:
        order_id = str(uuid.uuid4())
        
        # Simple balance check (mock)
        cost = price * size
        if side == "BUY":
            if self.balances.get("USD", 0) < cost:
                raise ValueError("Insufficient funds")
            self.balances["USD"] -= cost
        elif side == "SELL":
            base = product_id.split("-")[0]
            if self.balances.get(base, 0) < size:
                raise ValueError("Insufficient funds")
            self.balances[base] -= size

        self.orders[order_id] = {
            "id": order_id,
            "product_id": product_id,
            "side": side,
            "price": price,
            "size": size,
            "status": "OPEN",
            "created_at": time.time(),
            "filled_size": 0.0
        }
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            order = self.orders[order_id]
            if order["status"] == "OPEN":
                order["status"] = "CANCELED"
                # Refund logic would go here for a robust mock
                return True
        return False

    async def list_open_orders(self, product_id: Optional[str] = None) -> List[Any]:
        return [
            o for o in self.orders.values() 
            if o["status"] == "OPEN" and (product_id is None or o["product_id"] == product_id)
        ]

    async def get_fills(self, since: Optional[Any] = None) -> List[Any]:
        return []  # Mock fills implementation if needed

    async def stream_fills(self, callback: Any) -> None:
        pass  # No-op

    async def stream_ticker(self, product_ids: List[str], callback: Any) -> None:
        """
        Simulate ticker updates for the chart.
        """
        while True:
            for pid in product_ids:
                # Wiggle price by random +/- 0.05%
                current = self.current_prices.get(pid, 100.0)
                wiggle = current * 0.0005 * (1 if int(time.time()) % 2 == 0 else -1) # erratic
                new_price = current + wiggle
                self.current_prices[pid] = new_price
                
                # Emit
                await callback({
                    "type": "ticker",
                    "product_id": pid,
                    "price": new_price
                })
            
            await asyncio.sleep(1) # 1 sec update rate

    # Helper for tests to set price
    def set_mock_price(self, product_id: str, price: float):
        self.current_prices[product_id] = price

