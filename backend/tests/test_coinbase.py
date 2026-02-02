"""
Coinbase Adapter Integration Tests

These tests validate the Coinbase adapter's request signing and
structure WITHOUT making actual API calls. Run these BEFORE connecting
real API keys to ensure the adapter is correctly formatted.

For actual live tests, use the 'test_coinbase_sanity_check' test
which makes a single read-only API call to verify credentials.
"""
import pytest
import hmac
import hashlib
import time
from unittest.mock import AsyncMock, patch, MagicMock
from app.exchanges.coinbase import CoinbaseAdapter
from app.exchanges.interface import ExchangeAdapter


class TestCoinbaseSignature:
    """Tests for API signature generation"""
    
    def test_signature_format(self):
        """Signature must be 64-character hex string (SHA256)"""
        adapter = CoinbaseAdapter()
        adapter.api_secret = "test_secret_key"
        
        timestamp, signature = adapter._generate_signature("GET", "/api/v3/test", "")
        
        assert len(signature) == 64
        assert all(c in "0123456789abcdef" for c in signature)
    
    def test_signature_deterministic(self):
        """Same inputs must produce same signature"""
        adapter = CoinbaseAdapter()
        adapter.api_secret = "test_secret_key"
        
        # Mock time to get consistent timestamps
        with patch('time.time', return_value=1234567890):
            ts1, sig1 = adapter._generate_signature("GET", "/api/v3/test", "")
            ts2, sig2 = adapter._generate_signature("GET", "/api/v3/test", "")
        
        assert ts1 == ts2
        assert sig1 == sig2
    
    def test_signature_changes_with_method(self):
        """Different methods must produce different signatures"""
        adapter = CoinbaseAdapter()
        adapter.api_secret = "test_secret_key"
        
        with patch('time.time', return_value=1234567890):
            _, sig_get = adapter._generate_signature("GET", "/api/v3/test", "")
            _, sig_post = adapter._generate_signature("POST", "/api/v3/test", "")
        
        assert sig_get != sig_post
    
    def test_signature_includes_body(self):
        """POST body must affect signature"""
        adapter = CoinbaseAdapter()
        adapter.api_secret = "test_secret_key"
        
        with patch('time.time', return_value=1234567890):
            _, sig_empty = adapter._generate_signature("POST", "/api/v3/orders", "")
            _, sig_with_body = adapter._generate_signature("POST", "/api/v3/orders", '{"order": "data"}')
        
        assert sig_empty != sig_with_body


class TestCoinbaseOrderPayload:
    """Tests for order payload structure"""
    
    @pytest.mark.asyncio
    async def test_limit_order_payload_structure(self):
        """Verify limit order payload matches Coinbase API spec"""
        adapter = CoinbaseAdapter()
        adapter.api_key = "test_key"
        adapter.api_secret = "test_secret"
        
        # Mock the _request method to capture the payload
        captured_payload = None
        
        async def mock_request(method, endpoint, data=None):
            nonlocal captured_payload
            captured_payload = data
            return {"success": True, "order_id": "mock_order_123"}
        
        adapter._request = mock_request
        
        await adapter.place_limit_order(
            product_id="BTC-USD",
            side="BUY",
            price=45000.0,
            size=0.001,
            post_only=True
        )
        
        # Validate structure
        assert captured_payload is not None
        assert "client_order_id" in captured_payload
        assert captured_payload["product_id"] == "BTC-USD"
        assert captured_payload["side"] == "BUY"
        assert "order_configuration" in captured_payload
        
        config = captured_payload["order_configuration"]
        assert "limit_limit_gtc" in config
        assert config["limit_limit_gtc"]["base_size"] == "0.001"
        assert config["limit_limit_gtc"]["limit_price"] == "45000.0"
        assert config["limit_limit_gtc"]["post_only"] == True
    
    @pytest.mark.asyncio
    async def test_cancel_order_payload_structure(self):
        """Verify cancel order payload matches Coinbase API spec"""
        adapter = CoinbaseAdapter()
        adapter.api_key = "test_key"
        adapter.api_secret = "test_secret"
        
        captured_payload = None
        
        async def mock_request(method, endpoint, data=None):
            nonlocal captured_payload
            captured_payload = data
            return {"results": [{"order_id": "order_123", "success": True}]}
        
        adapter._request = mock_request
        
        await adapter.cancel_order("order_123")
        
        assert captured_payload is not None
        assert "order_ids" in captured_payload
        assert captured_payload["order_ids"] == ["order_123"]


class TestCoinbaseEndpoints:
    """Tests for correct endpoint paths"""
    
    @pytest.mark.asyncio
    async def test_products_endpoint(self):
        """Verify products endpoint path"""
        adapter = CoinbaseAdapter()
        adapter.api_key = "test_key"
        adapter.api_secret = "test_secret"
        
        captured_endpoint = None
        
        async def mock_request(method, endpoint, data=None):
            nonlocal captured_endpoint
            captured_endpoint = endpoint
            return {"products": []}
        
        adapter._request = mock_request
        await adapter.get_products()
        
        assert captured_endpoint == "/brokerage/products"
    
    @pytest.mark.asyncio
    async def test_balances_endpoint(self):
        """Verify accounts endpoint path"""
        adapter = CoinbaseAdapter()
        adapter.api_key = "test_key"
        adapter.api_secret = "test_secret"
        
        captured_endpoint = None
        
        async def mock_request(method, endpoint, data=None):
            nonlocal captured_endpoint
            captured_endpoint = endpoint
            return {"accounts": []}
        
        adapter._request = mock_request
        await adapter.get_balances()
        
        assert captured_endpoint == "/brokerage/accounts"
    
    @pytest.mark.asyncio
    async def test_open_orders_endpoint(self):
        """Verify open orders endpoint and query params"""
        adapter = CoinbaseAdapter()
        adapter.api_key = "test_key"
        adapter.api_secret = "test_secret"
        
        captured_endpoint = None
        
        async def mock_request(method, endpoint, data=None):
            nonlocal captured_endpoint
            captured_endpoint = endpoint
            return {"orders": []}
        
        adapter._request = mock_request
        await adapter.list_open_orders(product_id="BTC-USD")
        
        assert "/brokerage/orders/historical/batch" in captured_endpoint
        assert "order_status=OPEN" in captured_endpoint
        assert "product_id=BTC-USD" in captured_endpoint


class TestAdapterInterface:
    """Tests to ensure adapter implements interface correctly"""
    
    def test_coinbase_implements_interface(self):
        """CoinbaseAdapter must implement all ExchangeAdapter methods"""
        adapter = CoinbaseAdapter()
        
        required_methods = [
            'get_products',
            'get_balances', 
            'get_ticker',
            'place_limit_order',
            'cancel_order',
            'list_open_orders',
            'get_fills'
        ]
        
        for method in required_methods:
            assert hasattr(adapter, method), f"Missing required method: {method}"
            assert callable(getattr(adapter, method)), f"{method} is not callable"


# =============================================================================
# LIVE SANITY CHECK - Run with real keys (uses read-only endpoint)
# =============================================================================
@pytest.mark.skip(reason="Requires real API keys - run manually with: pytest -k test_coinbase_sanity -s")
@pytest.mark.asyncio
async def test_coinbase_sanity_check():
    """
    LIVE TEST: Makes a real API call to verify credentials work.
    Uses read-only endpoint (get_products) that costs nothing.
    
    Run manually: pytest backend/tests/test_coinbase.py::test_coinbase_sanity_check -s
    """
    adapter = CoinbaseAdapter()
    
    # This should NOT be empty if keys are configured
    assert adapter.api_key, "COINBASE_API_KEY not set in environment"
    assert adapter.api_secret, "COINBASE_API_SECRET not set in environment"
    
    # Make read-only API call
    products = await adapter.get_products()
    
    assert len(products) > 0, "No products returned - API may be misconfigured"
    
    # Verify BTC-USD exists
    btc_usd = [p for p in products if p.get("product_id") == "BTC-USD"]
    assert len(btc_usd) == 1, "BTC-USD not found in products"
    
    print(f"✅ API working! Found {len(products)} products")
    print(f"✅ BTC-USD status: {btc_usd[0].get('status', 'unknown')}")


@pytest.mark.skip(reason="Requires real API keys - run manually")
@pytest.mark.asyncio
async def test_coinbase_balance_check():
    """
    LIVE TEST: Verify we can read account balances.
    This confirms trading permissions.
    
    Run manually: pytest backend/tests/test_coinbase.py::test_coinbase_balance_check -s
    """
    adapter = CoinbaseAdapter()
    
    balances = await adapter.get_balances()
    
    print(f"✅ Balances retrieved:")
    for currency, amount in balances.items():
        if amount > 0:
            print(f"   {currency}: {amount}")
    
    # Should have at least USD available
    assert "USD" in balances or len(balances) > 0, "No balances found - check API permissions"


@pytest.mark.skip(reason="Requires real API keys - run manually")
@pytest.mark.asyncio  
async def test_coinbase_ticker_check():
    """
    LIVE TEST: Verify price fetching works.
    
    Run manually: pytest backend/tests/test_coinbase.py::test_coinbase_ticker_check -s
    """
    adapter = CoinbaseAdapter()
    
    price = await adapter.get_ticker("BTC-USD")
    
    assert price > 0, "Invalid price returned"
    print(f"✅ BTC-USD Price: ${price:,.2f}")
