# Project Specification: Autonomous Grid Trading Bot

## 1. Project Overview
**Goal:** Build a production-grade, lightweight, secure grid trading bot with a web dashboard.
**Primary Exchange:** Coinbase (USD pairs).
**Secondary Exchange:** Binance.US (Optional/Future).
**Core Strategy:** Grid trading with dynamic upward rebase (Model 1: Add-only), progressive order staging, and intelligent pruning.
**Key Attributes:** Restart-safe, mobile-friendly control, robust logging, strict risk management (kill switches).

---

## 2. Technical Stack & Architecture

### Backend
* **Language:** Python 3.11+
* **Framework:** FastAPI (REST API + Websockets)
* **Networking:** `httpx` (Async REST), `websockets` (Async streams)
* **Database:** SQLite via SQLAlchemy (Async)
* **Configuration:** Pydantic Settings (Env vars + .env file support)
* **Containerization:** Docker + Docker Compose

### Frontend
* **Framework:** React + Vite
* **Styling:** Tailwind CSS (Mobile-first design)
* **State:** Context API or lightweight store (Zustand/Jotai)
* **Comms:** Websocket client for live updates

### Deployment & Ops
* **Resilience:** Docker restart policies (`unless-stopped`).
* **CI/CD Prep:** `manage.ps1` (PowerShell) for standard commands (`.\manage.ps1 dev`, `.\manage.ps1 test`, `.\manage.ps1 down`).
* **Legacy:** `Makefile` retained for reference/Unix support.

---

## 3. Exchange Integration (Adapters)

### Interface: `ExchangeAdapter`
All exchanges must implement this abstract base class:
* `get_products() -> list[Product]`
* `get_balances() -> dict[str, float]` (USD and assets)
* `get_ticker(product_id) -> float`
* `place_limit_order(product_id, side, price, size, post_only=True) -> order_id`
* `cancel_order(order_id) -> bool`
* `list_open_orders(product_id=None) -> list[Order]`
* `get_fills(since=None) -> list[Fill]`
* `stream_fills(callback)` (Websocket preferred, Polling fallback)
* `stream_ticker(product_id, callback)`

### Implementation Details
* **CoinbaseAdapter (Primary):** Must handle specific Coinbase API rate limits with exponential backoff and jitter.
* **Security:** API Keys/Secrets must **only** be loaded from Environment Variables. **NEVER** log secrets.
* **Rate Limiting:** Implement a global request throttler per exchange.

---

## 4. Market Universe (Dynamic "Top 30")

The bot dynamically selects markets to trade to ensure liquidity and relevance.

### Logic
1.  **Fetch:** Get all tradable USD spot products from Coinbase.
2.  **Rank:** Rank by Market Cap (via CoinGecko API).
3.  **Filter:** Select Top 30 that match available Coinbase USD pairs.
4.  **Fallback:** If CoinGecko fails, rank by 24h Volume directly from Coinbase data.
5.  **Cache:** Refresh this list every 6 hours safely (do not disrupt active trades during refresh).

---

## 5. Strategy Engine

### 5.1 Configuration Defaults
* `grid_step_pct`: **0.33%** (0.0033)
* `per_order_pct`: **0.33%** of BotBudget per buy order.
* `max_grid_capital_pct`: **70%** (0.70) of total account value.
* `fee_buffer_pct`: **0.0%** (User configurable).

### 5.2 Bot Budget Modes
* **Fixed USD:** User sets a hard cap (e.g., $1000).
* **% of Account:** User sets % of total available USD (e.g., 50%).
* *Note:* Budget is re-calculated dynamically at runtime based on available balance.

### 5.3 Progressive Staging (The "Staging Band")
To prevent API spam and lock-up:
* **Band Depth:** Only maintain orders within **5%** (`0.05`) below the current price.
* **Order Count:** Maintain **10 (min)** to **25 (max)** buy orders per market.
* **Logic:**
    * If price drops, add new buys below.
    * If price rises, cancel "stale" buys that are > 5% below price (pruning).

### 5.4 Profit Logic
* **Mode "Step":** `Sell Price = Buy Price * (1 + grid_step_pct)`
* **Mode "Custom":** `Sell Price = Buy Price * (1 + custom_pct)`
* **Lot Lifecycle:**
    1.  Buy Fill detected.
    2.  Create "Lot" record (Buy Price, Size, Cost).
    3.  Immediately place paired Sell Order.
    4.  When Sell Fills -> Close Lot, realize profit.

### 5.5 Rebase (Model 1: Add-Only)
* **AnchorHigh:** Tracks the reference high price.
* **GridTop:** `AnchorHigh * (1 - buffer_pct)` (if buffer enabled).
* **Update Rule:** If `Current Price > AnchorHigh`, update `AnchorHigh` to current price.
* **Effect:** New buy orders are calculated from the new `GridTop`. **Do not** cancel existing orders solely for a rebase; only add new relevant ones.

### 5.6 Risk & Caps
* **Global Hard Cap:** **490** Open Orders (Coinbase limit - buffer).
* **Per-Market Soft Cap:** Prevent one coin from consuming all slots.
* **Stop Logic:** If `Inventory Used >= Max Capital`, enter **HOLD** mode (Stop buys, keep sells active).
* **Pruning Priority:**
    1.  Orders farthest from current price.
    2.  Oldest orders.
    3.  Orders outside the staging band.

---

## 6. Data Model (SQLite)

| Table | Description |
| :--- | :--- |
| `config` | Key-value pairs for persisted overrides & system version. |
| `markets` | Enabled/Disabled status per market, market-specific settings. |
| `orders` | `id`, `market`, `side`, `price`, `size`, `status`, `created_at`, `client_tag`. |
| `fills` | `id`, `order_id`, `market`, `side`, `price`, `fee`, `timestamp`. |
| `lots` | Link Buy Fill $\to$ Sell Order $\to$ Sell Fill. Tracks PnL and State. |
| `bot_state` | Singleton/Key-Val: Current Global State, `AnchorHigh` per market. |
| `audit_log` | User actions (Start/Stop, Config Change, Prune). |

---

## 7. API Specification (FastAPI)

### REST Endpoints
* `GET /api/status`: Bot state (RUNNING/PAUSED/HOLD), Uptime, Health.
* `GET /api/config`: Current strategy settings.
* `POST /api/config`: Update settings (validated).
* `POST /api/control/{action}`: `start`, `pause`, `prune`, `cancel_all`.
* `GET /api/markets`: List top 30, stats, toggle status.
* `POST /api/markets/{market}/{action}`: `enable`, `disable`.
* `GET /api/orders`: Filterable list of open orders.
* `GET /api/lots`: Filterable list of lots (PnL).
* `GET /healthz`: Kubernetes/Docker health check (DB + Exchange connection).

### Websocket (`/ws`)
* Push updates for: `price_update`, `order_filled`, `state_change`, `log_entry`.
* Payloads must be lightweight.

---

## 8. Frontend Dashboard Requirements

**Design:** Mobile-first, responsive, dark mode default.

1.  **Overview:**
    * Status Pill (RUNNING/PAUSED).
    * Budget/Inventory usage cards.
    * Global PnL summary.
    * Price Chart (Line) with `AnchorHigh` and `GridTop` overlay.
2.  **Markets:**
    * Table of Top 30.
    * Toggles for Enable/Disable.
    * Sparklines or simple stats (Vol, Change).
3.  **Orders & Inventory:**
    * Tab 1: Open Orders (Cancel button).
    * Tab 2: Active Lots (Unrealized PnL).
    * Tab 3: History/Closed Lots.
4.  **Controls/Settings:**
    * Form to edit `grid_step`, `budget`, etc.
    * "Emergency Stop" / "Cancel All" (Red Zone).
5.  **Logs:** Live streaming text log.

---

## 9. Operational Safety & Security

* **Flag:** `LIVE_TRADING_ENABLED` (Env Var). Default `false` (Paper Mode).
* **Paper Mode:** If false, mock all order placements and fills internally; do not hit exchange execution endpoints.
* **Startup Reconciliation:**
    1.  Load local DB state.
    2.  Fetch Exchange Open Orders.
    3.  **Reconcile:** Cancel orders unknown to DB; Import orders unknown to Exchange (or cancel them based on policy); Ensure Lot integrity.
* **Kill Switch:** UI button to "Stop & Cancel All".
* **Authentication:** Basic Auth for Dashboard/API access.

---

## 10. Repository Structure

```text
/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI Entrypoint
│   │   ├── bot/             # Core Engine (Strategy, State Machine)
│   │   ├── exchanges/       # Adapters (Coinbase, Mock)
│   │   ├── db/              # Models, CRUD
│   │   └── config/          # Settings logic
│   ├── tests/               # Pytest suite
│   └── requirements.txt
├── frontend/
│   ├── src/                 # React + Vite source
│   ├── package.json
│   └── Dockerfile
├── docker/
│   ├── Dockerfile.backend
│   └── docker-compose.yml
├── docs/
│   └── architecture.md
├── scripts/
│   ├── dev.sh
│   └── test.sh
├── .env.example
├── .env.example
├── manage.ps1       # Windows Task Runner
├── Makefile         # Legacy Unix Task Runner
├── README.md
└── SPEC.md