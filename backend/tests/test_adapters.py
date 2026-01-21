import pytest
from app.exchanges.mock import MockAdapter
from app.exchanges.coinbase import CoinbaseAdapter

@pytest.mark.asyncio
async def test_mock_adapter_lifecycle():
    adapter = MockAdapter()
    
    # 1. Get Balances
    balances = await adapter.get_balances()
    assert balances["USD"] == 10000.0
    
    # 2. Get Ticker
    price = await adapter.get_ticker("BTC-USD")
    assert price == 50000.0
    
    # 3. Place Order
    order_id = await adapter.place_limit_order(
        product_id="BTC-USD",
        side="BUY",
        price=49000.0,
        size=0.1
    )
    assert order_id is not None
    
    # 4. Check Open Orders
    orders = await adapter.list_open_orders()
    assert len(orders) == 1
    assert orders[0]["id"] == order_id
    
    # 5. Cancel Order
    canceled = await adapter.cancel_order(order_id)
    assert canceled is True
    
    orders_after = await adapter.list_open_orders()
    assert len(orders_after) == 0

def test_coinbase_signature_generation():
    """
    Unit test for signature generation logic.
    Does not make network requests.
    """
    # Mock settings by patching or setting env vars if needed
    # Here we just instantiate with dummy keys if the class allows,
    # or rely on it picking up empty strings and we test the logic.
    
    # Note: Adapter requires keys in settings. Checking if we can set them.
    # Since Settings is a singleton instantiated at import time, 
    # we might need to rely on the fact they default to "" or are patched.
    
    adapter = CoinbaseAdapter()
    adapter.api_secret = "secret"
    
    method = "GET"
    path = "/api/v3/brokerage/accounts"
    body = ""
    timestamp, sig = adapter._generate_signature(method, path, body)
    
    assert timestamp is not None
    assert len(sig) == 64  # SHA256 hex digest length
