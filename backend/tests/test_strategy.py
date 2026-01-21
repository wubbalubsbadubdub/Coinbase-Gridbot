import pytest
from app.bot.strategy import GridStrategy

def test_rebase_logic():
    strat = GridStrategy()
    
    # 1. Init
    anchor = strat.calculate_new_anchor(current_price=100.0, old_anchor=None)
    assert anchor == 100.0
    
    # 2. Price goes down -> Anchor stays
    anchor = strat.calculate_new_anchor(current_price=90.0, old_anchor=100.0)
    assert anchor == 100.0
    
    # 3. Price goes up -> Anchor moves up
    anchor = strat.calculate_new_anchor(current_price=110.0, old_anchor=100.0)
    assert anchor == 110.0

def test_buy_levels_generation():
    strat = GridStrategy(grid_step_pct=0.01, staging_band_pct=0.05) # 1% step, 5% band
    
    anchor = 100.0
    current_price = 100.0
    
    # Levels generated below 100: 99, 98.01, 97.02...
    # Band bottom: 95.0
    
    levels = strat.calculate_buy_levels(anchor, current_price)
    
    assert len(levels) > 0
    assert levels[0] < 100.0
    # First level should be 100 * 0.99 = 99.0
    assert abs(levels[0] - 99.0) < 0.001
    
    # Check that all levels are > 95.0
    for price in levels:
        assert price > 95.0

def test_pruning_logic():
    strat = GridStrategy(staging_band_pct=0.10) # 10% band
    current_price = 100.0
    limit = 90.0 # 100 * 0.9
    
    # 91 is inside band
    assert strat.should_prune(91.0, current_price) is False
    
    # 89 is outside band
    assert strat.should_prune(89.0, current_price) is True

def test_sell_price():
    strat = GridStrategy(grid_step_pct=0.10) # 10% profit
    buy_price = 100.0
    sell_price = strat.get_sell_price(buy_price)
    assert abs(sell_price - 110.0) < 0.001
