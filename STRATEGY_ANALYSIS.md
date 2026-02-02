# Strategy Analysis Report

## Part 1: The "Coinbase Gridbot" Strategy Definition

### 1. Core Philosophy: Add-Only Rebase (Volatility Harvesting)

This trading system is **not trying to predict price direction**. Instead, it accepts the fundamental truth that crypto prices fluctuate constantly and aims to profit from that volatility itself.

**The Core Concept:**

*   We maintain a "grid" of buy orders stacked below the current price.
*   When price dips, orders fill. When price recovers, we sell for a small, guaranteed profit.
*   This creates a consistent income stream during sideways churning—the most common market condition.

**"Add-Only Rebase":**

The `AnchorHigh` (our reference point) **only moves upward**. If the price makes a new high, the anchor resets. This means:

1.  **We never chase losses.** We don't cancel existing buy orders just because the price went up. We let them stay, ready to catch the next dip.
2.  **We adapt to bullish momentum.** Our grid "floats up" with the market, keeping buy levels relevant.
3.  **We naturally accumulate during dips.** If the price falls steadily, we buy more at progressively lower prices. These positions are held ("bag-held") until price recovers—we **never sell at a loss**.

---

### 2. Buy Logic (The Entry)

#### A. Anchor High & Top Buffer ("No Trade Zone")

The system tracks a **Session High (`AnchorHigh`)**—the highest price seen since the bot started or since last manual reset.

*   **`GridTop`**: The absolute highest price at which we would place a buy. This is typically equal to `AnchorHigh`, but a configurable **Buffer** can push it lower.

    > **Example:** If `AnchorHigh = $100` and `Buffer = 5%`, then `GridTop = $95`. This means we will **never** place a buy order above $95, creating a "No Trade Zone" at the very top to avoid buying at all-time-highs.

*   **Why?** Buying at a peak is the #1 way to get stuck in an underwater position. The buffer acts as a safety margin.

#### B. Progressive Staging ("Staging Band")

Traditional grid bots place ALL grid levels at once (e.g., 100 orders from current price to 50% down). This has problems:
*   It locks up capital.
*   It spams the exchange with orders (leading to rate limits/bans).
*   Most of those orders will never fill.

**Our Solution: The "Staging Band" (Default: 5% below current price)**

| Metric | Value |
|---|---|
| Staging Band Depth | 5% below current price |
| Orders Maintained | 10-25 (configurable) |

*   **Dynamic Placement:** Only orders within this 5% window are ever placed. If price is $100, we only have orders between ~$100 and ~$95.
*   **Pruning:** If price rises and an order is now >5% below price, it's automatically **canceled** (pruned).
*   **Addition:** If price drops and new grid levels enter the 5% window, they are automatically **added**.

**Result:** A lean, constantly-adjusting grid that follows the price without consuming API limits or locking capital on distant, unlikely fills.

---

### 3. Sell Logic (The 4 Profit Modes)

When a buy order fills, we immediately place a paired sell order. The sell price is determined by the active **Profit Mode**.

| Mode | Sell Price Formula | Use Case |
|---|---|---|---|
| **STEP (Fixed Income)** | `Buy Price × (1 + grid_step_pct)` (e.g., +0.33%) | Conservative cash flow. Sell ASAP for tiny, consistent profits. |
| **STEP_REINVEST (Compounding)** | Same as STEP, but profits are immediately recycled into larger buy sizes. | Aggressive growth. Compound returns by reinvesting every penny. |
| **CUSTOM (Swing Trading)** | `Buy Price × (1 + custom_target_pct)` (e.g., +1.5%) | Targeting larger swings. Useful for volatile alt-coins where waiting for a bigger pop is more efficient. |
| **SMART_REINVEST (Monthly Target Hybrid)** | Standard size **until** monthly profit target (e.g., $1000 USD) is reached. After that, switch to larger, compounding sizes. | Best of both worlds. Secure a "salary" first, then play with house money to compound. |

**Smart Reinvest Deep Dive:**

This mode queries the database for the **running monthly profit total (`current_month_profit_usd`)**. The counter resets on the 1st of each month.

*   **Pre-Target Logic:** Use a smaller, conservative lot size to minimize risk while building towards the target.
*   **Post-Target Logic:** The "target" is met. Now, every additional dollar is "gravy," so the bot increases lot sizes to accelerate compounding.

---

### 4. Key Technical Features

| Feature | Description |
|---|---|
| **"Highlander" Mode** | Only **one** market can be actively trading (`enabled = True`) at any given time. This enforces focus and prevents capital fragmentation. Trying to start a new market auto-stops the previous one. |
| **Emergency Kill Switch** | A prominent "STOP ALL" button in the UI immediately halts the bot loop and sends cancel requests for **every** open order on all markets. |
| **WebSocket Architecture** | The backend maintains a real-time WebSocket connection to the frontend. Price updates, fill notifications, and bot state changes are pushed instantly—no polling lag. |
| **Paper Mode** | Built-in simulation mode (`PAPER_MODE=True`) that uses real market data but simulates order fills internally since no exchange API calls are made. Essential for testing. |
| **Progressive Order ID Tracking** | Every order placed is logged to a SQLite database with its current status (`OPEN`, `FILLED`, `CANCELED`). The engine reconciles local state with exchange state on each tick. |

---
---

## Part 2: Freqtrade Feasibility Study

[Freqtrade](https://www.freqtrade.io/en/stable/) is a popular, open-source Python crypto trading bot. This section analyzes whether it could replace our custom build.

### 1. Grid Capabilities: Does Freqtrade have native Grid Trading?

| Question | Finding |
|---|---|
| **Native Grid Mode?** | **No.** Freqtrade is fundamentally a **signal-based bot**. Its core loop is: "Analyze candle data with TA-lib (RSI, MACD, Bollinger) → If `enter_long` signal true, execute **one** market/limit order." |
| **Active Order Management?** | **Limited.** Freqtrade manages *trades* (a single open position), not a *ladder of pending limit orders*. It has no built-in concept of "maintain 15 open buy limit orders at specific price levels." |
| **Community Grid Strategies?** | **Yes, but DIY.** Some community strategies (e.g., `Discord_GridV6`) attempt to replicate grid logic, but they require writing **significant custom Python code** within Freqtrade's strategy class. |

**Verdict:** Freqtrade is designed for "one signal, one trade" patterns, not "maintain a dynamic ladder of limit orders."

---

### 2. "Add-Only" Logic: Can Freqtrade ensure we never sell at a loss?

| Question | Finding |
|---|---|
| **Stoploss Disabling?** | Yes, you can set `stoploss = -1.0` (effectively disabled). This prevents automatic loss cutting. |
| **"Bag Holding" Support?** | **Implicit, not explicit.** Freqtrade will hold a position indefinitely if no sell signal is generated. However, it's designed around *closing trades*, not perpetual holding. |
| **Lot-based Tracking?** | **No.** Freqtrade tracks a single *trade* per pair. Our system tracks individual *lots* (a buy and its paired sell). Freqtrade has no native concept of "I have 10 separate buy fills, each needing its own exit price." |

**Verdict:** While you can prevent automatic loss selling, Freqtrade's single-trade-per-pair model doesn't map to our lot-based system where we accumulate multiple distinct buy positions.

---

### 3. Progressive Staging: Can Freqtrade limit orders to a % range?

| Question | Finding |
|---|---|
| **Placing Multiple Pending Orders?** | **No native support.** Freqtrade places an order when a signal fires, not a set of orders in advance. There's no "OrderBook" class you can populate with pending limits. |
| **Max Open Trades?** | Yes, `max_open_trades` limits how many *concurrent trades* the bot manages. But this is trades (positions), not pending unfilled orders. |
| **Simulating Staging Band?** | You *could* write a custom callback that uses the Coinbase API directly inside a strategy. But at that point, you're just embedding our custom logic into Freqtrade—negating its benefits. |

**Verdict:** Freqtrade has no mechanism for a "staging band" of pending limit orders. All logic for placing/pruning orders would have to be custom code.

---

### 4. Custom Profit Logic (Smart Reinvest): Is this possible?

| Question | Finding |
|---|---|
| **Accessing External DB?** | **Possible, but unsupported.** You could add `import sqlite3` inside your strategy and query a custom table. However, Freqtrade's architecture doesn't encourage this; its strategies are meant to be stateless dataframe operations. |
| **Monthly Profit Tracking?** | **Not built-in.** Freqtrade exposes `profit_pct` on individual trades. Aggregating monthly USD profit requires custom code. |
| **Dynamic Sizing?** | Freqtrade has a `stake_amount` concept, but it's set in config, not dynamically adjusted based on an external monthly counter. |

**Verdict:** Extremely difficult. "Smart Reinvest" (choosing lot size based on a running monthly profit total from a database) would require heavily custom code that essentially replicates what our `BotEngine` already does.

---

## Conclusion: Custom Build vs. Freqtrade

| Criterion | Freqtrade | Our Custom Build | Winner |
|---|---|---|---|
| **Grid Order Management** | Not native. Requires full DIY. | Core feature. | ✅ Custom |
| **Progressive Staging / Pruning** | No support. | Native with Staging Band logic. | ✅ Custom |
| **Lot-based PnL Tracking** | No. Tracks single trades. | Yes. Individual Buy → Sell lots. | ✅ Custom |
| **Smart Reinvest / Monthly Target** | Requires deep hacks. | Native DB integration. | ✅ Custom |
| **Backtesting** | Excellent, built-in. | None currently. | ✅ Freqtrade |
| **Community / Ecosystem** | Large, active. | Single-developer. | ✅ Freqtrade |
| **Maintenance Burden** | Maintained by others. | Maintained by you. | ✅ Freqtrade |

---

### Final Verdict: **Stick with the Custom Build.**

Freqtrade is a powerful tool for **signal-based trading** (e.g., "Buy when RSI < 30, sell when RSI > 70"). It is **not designed** for real-time grid order management, progressive staging, or the unique "Add-Only Rebase" model.

Attempting to implement this strategy in Freqtrade would require:
1.  Ignoring Freqtrade's signal system entirely.
2.  Writing custom Python that directly manages Coinbase API calls.
3.  Maintaining your own lot/order state outside Freqtrade's trade model.

**At that point, you're just using Freqtrade as a scheduler, negating its core value.** Our custom FastAPI + WebSocket + SQLite architecture is purpose-built for this specific strategy and remains the correct choice.

> **Future Consideration:** If you ever want to add signal-based *filtering* (e.g., "only grid trade BTC when daily RSI > 40"), a Freqtrade sidecar for market sentiment could complement the custom bot. But the core execution engine should remain custom.
