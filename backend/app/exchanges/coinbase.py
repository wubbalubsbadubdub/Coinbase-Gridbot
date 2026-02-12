import time
import json
import logging
import asyncio
import uuid
import secrets
from typing import List, Dict, Any, Optional
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
import jwt

from app.exchanges.interface import ExchangeAdapter
from app.config import settings

logger = logging.getLogger(__name__)

class CoinbaseAdapter(ExchangeAdapter):
    """
    Coinbase Advanced Trade API Adapter.
    Uses JWT/ES256 authentication for CDP API keys.
    Docs: https://docs.cloud.coinbase.com/advanced-trade-api/docs/rest-api-overview
    """
    BASE_URL = "https://api.coinbase.com/api/v3"

    def __init__(self):
        self.api_key = settings.COINBASE_API_KEY
        self.api_secret = settings.COINBASE_API_SECRET
        
        if not self.api_key or not self.api_secret:
            logger.warning("Coinbase API keys not set. Adapter will fail on requests.")

    def _build_jwt(self, method: str, path: str) -> str:
        """
        Build a JWT token for CDP API authentication.
        Uses ES256 (ECDSA with P-256 curve and SHA-256).
        """
        # Parse the private key
        private_key_pem = self.api_secret
        
        # Handle escaped newlines from environment variables
        if "\\n" in private_key_pem:
            private_key_pem = private_key_pem.replace("\\n", "\n")
        
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem.encode("utf-8"),
                password=None
            )
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise ValueError(f"Invalid private key format: {e}")

        # JWT header
        headers = {
            "alg": "ES256",
            "kid": self.api_key,  # The API key ID
            "nonce": secrets.token_hex(16),  # Random nonce
            "typ": "JWT"
        }
        
        # JWT payload
        uri = f"{method} api.coinbase.com{path}"
        now = int(time.time())
        
        payload = {
            "iss": "coinbase-cloud",
            "nbf": now,
            "exp": now + 120,  # 2 minute expiry
            "sub": self.api_key,
            "uri": uri
        }
        
        # Sign the JWT
        token = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
        return token

    async def _request(self, method: str, endpoint: str, data: Dict[str, Any] = None, retry_count: int = 0) -> Dict[str, Any]:
        """
        Make an authenticated request to Coinbase API with automatic rate limit handling.
        """
        MAX_RETRIES = 3
        
        url = f"{self.BASE_URL}{endpoint}"
        body_str = json.dumps(data) if data else ""
        
        # Path for JWT includes /api/v3
        path_for_jwt = f"/api/v3{endpoint}"

        jwt_token = self._build_jwt(method.upper(), path_for_jwt)
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(method, url, headers=headers, content=body_str if data else None)
                
                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    if retry_count >= MAX_RETRIES:
                        logger.error(f"Rate limit exceeded after {MAX_RETRIES} retries for {endpoint}")
                        raise Exception("Rate limit exceeded - max retries reached")
                    
                    # Get retry delay from header, default to exponential backoff
                    retry_after = response.headers.get("Retry-After", str(2 ** retry_count))
                    wait_time = float(retry_after)
                    
                    logger.warning(f"Rate limited on {endpoint}. Waiting {wait_time}s before retry {retry_count + 1}/{MAX_RETRIES}")
                    await asyncio.sleep(wait_time)
                    
                    # Retry with incremented count
                    return await self._request(method, endpoint, data, retry_count + 1)
                
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"Coinbase API Error: {e.response.text if hasattr(e, 'response') else str(e)}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Network Error: {e}")
                raise

    async def get_products(self) -> List[Any]:
        """Get all available trading products."""
        data = await self._request("GET", "/brokerage/products")
        return data.get("products", [])

    async def get_balances(self) -> Dict[str, float]:
        """Get account balances."""
        data = await self._request("GET", "/brokerage/accounts")
        accounts = data.get("accounts", [])
        
        balances = {}
        for acc in accounts:
            currency = acc.get("currency")
            available = float(acc.get("available_balance", {}).get("value", 0))
            if currency and available > 0:
                balances[currency] = available
        return balances

    async def get_ticker(self, product_id: str) -> float:
        """Get current price for a product."""
        # Use the product endpoint to get best bid/ask
        data = await self._request("GET", f"/brokerage/products/{product_id}")
        
        # Price from product data
        price = data.get("price")
        if price:
            return float(price)
            
        # Fallback to quote_increment_price or default
        return float(data.get("quote_increment_price", 0))

    async def get_product_candles(self, product_id: str, start: int, end: int, granularity: str) -> List[Dict]:
        """
        Get historical candle data.
        granularity: ONE_MINUTE, FIVE_MINUTE, FIFTEEN_MINUTE, ONE_HOUR, SIX_HOUR, ONE_DAY
        timestamps: UNIX timestamp (int)
        """
        params = f"?start={start}&end={end}&granularity={granularity}"
        data = await self._request("GET", f"/brokerage/products/{product_id}/candles{params}")
        return data.get("candles", [])

    async def place_limit_order(self, product_id: str, side: str, price: float, size: float, post_only: bool = True) -> str:
        """
        Place a limit order.
        Returns the order ID.
        """
        client_order_id = str(uuid.uuid4())
        
        order_config = {
            "limit_limit_gtc": {
                "base_size": str(size),
                "limit_price": str(round(price, 2)),
                "post_only": post_only
            }
        }
        
        payload = {
            "client_order_id": client_order_id,
            "product_id": product_id,
            "side": side.upper(),
            "order_configuration": order_config
        }
        
        logger.info(f"Placing {side} order: {size} @ {price} on {product_id}")
        result = await self._request("POST", "/brokerage/orders", payload)
        
        # Extract order ID from response
        order_id = result.get("order_id") or result.get("success_response", {}).get("order_id")
        if not order_id:
            logger.error(f"Failed to get order ID from response: {result}")
            raise Exception(f"Order placement failed: {result}")
        
        logger.info(f"Order placed successfully: {order_id}")
        return order_id

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        try:
            payload = {"order_ids": [order_id]}
            result = await self._request("POST", "/brokerage/orders/batch_cancel", payload)
            
            # Check if cancellation was successful
            results = result.get("results", [])
            if results:
                success = results[0].get("success", False)
                if success:
                    logger.info(f"Order {order_id} canceled successfully")
                    return True
                else:
                    failure_reason = results[0].get("failure_reason", "Unknown")
                    logger.warning(f"Failed to cancel order {order_id}: {failure_reason}")
                    return False
            
            return False
        except Exception as e:
            logger.error(f"Error canceling order {order_id}: {e}")
            return False

    async def list_open_orders(self, product_id: str = None) -> List[Dict]:
        """List open orders, optionally filtered by product."""
        params = "?order_status=OPEN"
        if product_id:
            params += f"&product_id={product_id}"
        
        data = await self._request("GET", f"/brokerage/orders/historical/batch{params}")
        return data.get("orders", [])

    async def get_fills(self, since: float = None) -> List[Dict]:
        """Get recent fills."""
        params = ""
        if since:
            params = f"?start_sequence_timestamp={int(since * 1000)}"
        
        data = await self._request("GET", f"/brokerage/orders/historical/fills{params}")
        return data.get("fills", [])

    async def stream_fills(self, callback):
        """Stream fills via WebSocket (not implemented for paper trading)."""
        logger.warning("WebSocket streaming not implemented for Coinbase adapter")
        pass

    async def stream_ticker(self, product_ids: List[str], callback):
        """
        Stream ticker updates via WebSocket.
        Subscribes to the public 'ticker' channel on Coinbase Advanced Trade API.
        """
        import websockets
        uri = "wss://advanced-trade-ws.coinbase.com"
        
        logger.info(f"Connecting to Coinbase WS for tickers: {product_ids}")
        
        while True:
            try:
                async with websockets.connect(uri) as websocket:
                    # Subscribe
                    subscribe_msg = {
                        "type": "subscribe",
                        "product_ids": product_ids,
                        "channel": "ticker"
                    }
                    await websocket.send(json.dumps(subscribe_msg))
                    logger.info(f"Subscribed to tickers for {len(product_ids)} products")
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            
                            # Handle different message structures
                            events = data.get("events", [])
                            for event in events:
                                tickers = event.get("tickers", [])
                                for ticker in tickers:
                                    if "price" in ticker and "product_id" in ticker:
                                        fmt_data = {
                                            "type": "ticker",
                                            "product_id": ticker["product_id"],
                                            "price": float(ticker["price"])
                                        }
                                        await callback(fmt_data)
                        except Exception as parse_error:
                            logger.error(f"WS Parse Error: {parse_error}")
                            
            except Exception as e:
                logger.error(f"WebSocket Connection Error: {e}")
                logger.info("Reconnecting to WS in 5 seconds...")
                await asyncio.sleep(5)
