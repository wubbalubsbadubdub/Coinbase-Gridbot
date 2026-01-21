from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class ExchangeAdapter(ABC):
    """
    Abstract base class that all exchange adapters must implement.
    Defined in SPEC.md Section 3.
    """

    @abstractmethod
    async def get_products(self) -> List[Any]:
        """Fetch all tradable products."""
        pass

    @abstractmethod
    async def get_balances(self) -> Dict[str, float]:
        """Fetch balances for all assets (e.g. {'USD': 1000.0, 'BTC': 0.5})."""
        pass

    @abstractmethod
    async def get_ticker(self, product_id: str) -> float:
        """Fetch current price for a product."""
        pass

    @abstractmethod
    async def place_limit_order(self, product_id: str, side: str, price: float, size: float, post_only: bool = True) -> str:
        """Place a limit order and return the order ID."""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID."""
        pass

    @abstractmethod
    async def list_open_orders(self, product_id: Optional[str] = None) -> List[Any]:
        """List currently open orders."""
        pass

    @abstractmethod
    async def get_fills(self, since: Optional[Any] = None) -> List[Any]:
        """Fetch fills/trades history."""
        pass

    @abstractmethod
    async def stream_fills(self, callback: Any) -> None:
        """Stream fill events to a callback."""
        pass

    @abstractmethod
    async def stream_ticker(self, product_ids: List[str], callback: Any) -> None:
        """Stream ticker updates to a callback."""
        pass
