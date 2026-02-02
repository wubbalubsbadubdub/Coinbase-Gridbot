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
        self.balances = {"USD": 10000.0, "BTC": 0.5, "ETH": 5.0}
        self.orders = {}
        
        # Realistic mock keys for expanded product list
        self.mock_products = [
            "BTC-USD", "ETH-USD", "SOL-USD", "ADA-USD", "AVAX-USD",
            "DOGE-USD", "SHIB-USD", "MATIC-USD", "DOT-USD", "LTC-USD",
            "LINK-USD", "UNI-USD", "ATOM-USD", "XLM-USD", "BCH-USD",
            "ALGO-USD", "FIL-USD", "VET-USD", "ICP-USD", "SAND-USD"
        ]
        
        # Initialize random prices for them
        self.current_prices = {
            "BTC-USD": 45000.0,
            "ETH-USD": 2800.0,
            "SOL-USD": 95.0,
            "ADA-USD": 0.55,
            "AVAX-USD": 35.0,
            "DOGE-USD": 0.08,
            "SHIB-USD": 0.00001,
            "MATIC-USD": 0.85,
            "DOT-USD": 7.50,
            "LTC-USD": 70.0,
            "LINK-USD": 15.0,
            "UNI-USD": 6.50,
            "ATOM-USD": 10.0,
            "XLM-USD": 0.12,
            "BCH-USD": 250.0,
            "ALGO-USD": 0.18,
            "FIL-USD": 5.50,
            "VET-USD": 0.03,
            "ICP-USD": 12.0,
            "SAND-USD": 0.45
        }

    async def get_account(self):
        """Mock account balance"""
        return {
            "balance": self.balances["USD"],
            "currency": "USD"
        }

    async def get_products(self):
        """Return expanded list of mock products with volume"""
        import random
        products = []
        for pair in self.mock_products:
            base = pair.split("-")[0]
            # Generate consistent but random-looking volume
            vol = random.randint(100000, 10000000)
            if base in ["BTC", "ETH", "SOL"]:
                vol *= 10
            
            products.append({
                "id": pair,
                "base_currency": base,
                "quote_currency": "USD",
                "display_name": pair,
                "volume_24h": float(vol),
                "status": "online"
            })
        return products

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

