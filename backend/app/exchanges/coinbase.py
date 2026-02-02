import hmac
import hashlib
import time
import json
import logging
import asyncio
import uuid
from typing import List, Dict, Any, Optional
import httpx
from app.exchanges.interface import ExchangeAdapter
from app.config import settings

logger = logging.getLogger(__name__)

class CoinbaseAdapter(ExchangeAdapter):
    """
    Coinbase Advanced Trade API Adapter.
    Docs: https://docs.cloud.coinbase.com/advanced-trade-api/docs/rest-api-overview
    """
    BASE_URL = "https://api.coinbase.com/api/v3"

    def __init__(self):
        self.api_key = settings.COINBASE_API_KEY
        self.api_secret = settings.COINBASE_API_SECRET
        
        if not self.api_key or not self.api_secret:
            logger.warning("Coinbase API keys not set. Adapter will fail on requests.")

    def _generate_signature(self, method: str, path: str, body: str = "") -> str:
        timestamp = str(int(time.time()))
        message = timestamp + method + path + body
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return timestamp, signature

    async def _request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{endpoint}"
        body_str = json.dumps(data) if data else ""
        
        # Path for signature must exclude the domain, include /api/v3
        path_for_sign = f"/api/v3{endpoint}"

        timestamp, signature = self._generate_signature(method.upper(), path_for_sign, body_str)
        
        headers = {
            "CB-ACCESS-KEY": self.api_key,
            "CB-ACCESS-SIGN": signature,
            "CB-ACCESS-TIMESTAMP": timestamp,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, content=body_str)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Coinbase API Error: {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Network Error: {e}")
                raise # Re-raise for now so engine knows to try again next tick, but log it clearly

    async def get_products(self) -> List[Any]:
        # GET /brokerage/products
        data = await self._request("GET", "/brokerage/products")
        return data.get("products", [])

    async def get_balances(self) -> Dict[str, float]:
        # GET /brokerage/accounts
        data = await self._request("GET", "/brokerage/accounts")
        accounts = data.get("accounts", [])
        
        balances = {}
        for acc in accounts:
            currency = acc["currency"]
            available = float(acc["available_balance"]["value"])
            if available > 0:
                balances[currency] = available
        return balances

    async def get_ticker(self, product_id: str) -> float:
        # 1. Check Cache (WebSocket)
        cached = self.get_ticker_cached(product_id)
        if cached:
            return cached

        # 2. Fallback to REST
        # GET /brokerage/products/{product_id}
        # Note: Coinbase API structure might vary, strictly looking for price
        data = await self._request("GET", f"/brokerage/products/{product_id}")
        price = data.get("price")
        if not price:
            return 0.0
        return float(price)

    async def place_limit_order(self, product_id: str, side: str, price: float, size: float, post_only: bool = True) -> str:
        # POST /brokerage/orders
        payload = {
            "client_order_id": str(uuid.uuid4()),
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": {
                "limit_limit_gtc": {
                    "base_size": str(size),
                    "limit_price": str(price),
                    "post_only": post_only
                }
            }
        }
        data = await self._request("POST", "/brokerage/orders", payload)
        # Response: { "success": true, "order_id": "...", ... }
        if not data.get("success"):
            error_response = data.get("error_response", {})
            raise ValueError(f"Order failed: {error_response}")
            
        return data.get("order_id")

    async def cancel_order(self, order_id: str) -> bool:
        # POST /brokerage/orders/batch_cancel
        payload = {"order_ids": [order_id]}
        data = await self._request("POST", "/brokerage/orders/batch_cancel", payload)
        results = data.get("results", [])
        for res in results:
            if res.get("order_id") == order_id:
                return res.get("success", False)
        return False

    async def list_open_orders(self, product_id: Optional[str] = None) -> List[Any]:
        # GET /brokerage/orders/historical/batch
        # Need to verify if this is the correct endpoint for OPEN orders.
        # Advanced Trade API uses "GET /brokerage/orders/historical/batch" with order_status="OPEN"
        params = "?order_status=OPEN"
        if product_id:
            params += f"&product_id={product_id}"
            
        data = await self._request("GET", f"/brokerage/orders/historical/batch{params}")
        return data.get("orders", [])

    async def get_fills(self, since: Optional[Any] = None) -> List[Any]:
        # GET /brokerage/orders/historical/fills
        endpoint = "/brokerage/orders/historical/fills"
        if since:
            endpoint += f"?start_sequence={since}"
        data = await self._request("GET", endpoint)
        return data.get("fills", [])

    
    async def _ws_connect(self, channels: List[str], product_ids: List[str], callback: Any):
        """
        Generic WebSocket connection handler.
        """
        import websockets
        WS_URL = "wss://advanced-trade-ws.coinbase.com"
        
        while True:
            try:
                async with websockets.connect(WS_URL) as ws:
                    # 1. Sign
                    timestamp = str(int(time.time()))
                    str_to_sign = f"{timestamp}usersselfverify"
                    signature = hmac.new(
                        self.api_secret.encode("utf-8"),
                        str_to_sign.encode("utf-8"),
                        hashlib.sha256
                    ).hexdigest()
                    
                    # 2. Subscribe
                    msg = {
                        "type": "subscribe",
                        "product_ids": product_ids,
                        "channel": channels[0], # Advanced Trade WS usually takes separate subs or check docs strictly
                        "signature": signature,
                        "key": self.api_key,
                        "timestamp": timestamp,
                    }
                    if len(channels) > 1:
                         # For now, simple support for one channel type per call or loop
                         pass

                    await ws.send(json.dumps(msg))
                    logger.info(f"Subscribed to {channels} for {product_ids}")
                    
                    # 3. Listen
                    async for message in ws:
                        data = json.loads(message)
                        await callback(data)
                        
            except Exception as e:
                logger.error(f"WebSocket Error: {e}")
                await asyncio.sleep(5) # Backoff

    def get_ticker_cached(self, product_id: str) -> Optional[float]:
        """
        Returns cached price if available.
        """
        # We need a shared cache. Initializing it in __init__ is better, 
        # but for now we'll inject it into the class or use a singleton approach.
        # Let's add it to __init__ via a separate edit or assume it exists.
        return getattr(self, "price_cache", {}).get(product_id)

    async def stream_ticker(self, product_ids: List[str], callback: Any) -> None:
        """
        Streams ticker updates.
        """
        # Ensure cache exists
        if not hasattr(self, "price_cache"):
            self.price_cache = {}
            
        async def internal_callback(data):
            # Parse 'ticker' channel events
            if data.get("channel") == "ticker":
                events = data.get("events", [])
                for event in events:
                    tickers = event.get("tickers", [])
                    for tick in tickers:
                        pid = tick["product_id"]
                        price = float(tick["price"])
                        self.price_cache[pid] = price
                        # Forward to external callback if needed
                        # await callback(pid, price) 
            
        await self._ws_connect(["ticker"], product_ids, internal_callback)

    async def stream_fills(self, callback: Any) -> None:
        """
        Stream user fills.
        """
        async def internal_callback(data):
            if data.get("channel") == "user":
                # Check for fills logic
                pass
        
        # User channel doesn't need product_ids usually, but check docs.
        # For MVP, we reserve this.
        pass

