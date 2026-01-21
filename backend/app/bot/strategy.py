from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple

class GridStrategy:
    """
    Pure logic for Grid Trading (SPEC Section 5).
    All prices/math should handle floats cautiously or use Decimal if precision is critical.
    For this implementation, we use float for performance but round explicitly where needed for APIs.
    """

    def __init__(self, 
                 grid_step_pct: float = 0.0033,  # 0.33%
                 staging_band_pct: float = 0.05, # 5%
                 max_orders: int = 490,
                 buffer_enabled: bool = False,
                 buffer_pct: float = 0.0):
        self.grid_step_pct = grid_step_pct
        self.staging_band_pct = staging_band_pct
        self.max_orders = max_orders
        self.buffer_enabled = buffer_enabled
        self.buffer_pct = buffer_pct

    def calculate_new_anchor(self, current_price: float, old_anchor: Optional[float]) -> float:
        """
        Rebase Logic (Model 1: Add-Only).
        If current_price > old_anchor, update anchor.
        Only updates UPWARDS.
        """
        if old_anchor is None:
            return current_price
        
        if current_price > old_anchor:
            return current_price
        
        return old_anchor

    def calculate_buy_levels(self, anchor_high: float, current_price: float) -> List[float]:
        """
        Calculates grid levels within the Staging Band (5% below current price).
        Levels are calculated from AnchorHigh (or GridTop if buffer active) downwards.
        """
        buy_levels = []
        
        # Calculate Grid Top
        # If buffer enabled: GridTop = AnchorHigh * (1 - buffer_pct)
        # Else: GridTop = AnchorHigh
        grid_top = anchor_high
        if self.buffer_enabled and self.buffer_pct > 0:
            grid_top = anchor_high * (1 - self.buffer_pct)
        
        lower_bound = current_price * (1 - self.staging_band_pct)
        
        # Determine first level
        # Level 1 is one step below GridTop
        level_price = grid_top * (1 - self.grid_step_pct)
        
        # Generate levels downwards
        while level_price > lower_bound:
            # We only place a buy if it is BELOW current price (with a tiny margin to avoid immediate fill/taker fees if desired, 
            # but usually just < current_price is enough for a limit order).
            if level_price < current_price:
                buy_levels.append(level_price)
            
            # Next level down
            level_price = level_price * (1 - self.grid_step_pct)
            
            # Safety break
            if len(buy_levels) > self.max_orders:
                break
                
        return buy_levels

    def get_sell_price(self, buy_price: float) -> float:
        """
        Mode "Step": Sell Price = Buy Price * (1 + grid_step_pct)
        """
        return buy_price * (1 + self.grid_step_pct)

    def should_prune(self, order_price: float, current_price: float) -> bool:
        """
        Prune if order is outside the staging band (Too far below).
        """
        lower_bound = current_price * (1 - self.staging_band_pct)
        return order_price < lower_bound
