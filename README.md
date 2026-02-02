# Josh's Coinbase Gridbot

A production-grade, autonomous grid trading bot for Coinbase (USD pairs).

## Quick Start (Windows)

This project is optimized for Windows development using PowerShell.

### Prerequisites
* Docker Desktop for Windows
* PowerShell

### Commands

We use `manage.ps1` to handle Docker orchestration.

**Start Development Environment:**
```powershell
.\manage.ps1 dev
# Starts Backend (localhost:8000) and Frontend (localhost:5173)
```

**Stop Environment:**
```powershell
.\manage.ps1 down
```

**Run Tests:**
```powershell
.\manage.ps1 test
```

## Verify Coinbase API Credentials

Before going live, run these manual tests to verify your API keys work correctly. These tests are skipped by default during `.\manage.ps1 test` because they require real API credentials configured in your `.env` file.

> **Note:** All three tests are **read-only** and will NOT place any orders or modify your account.

**1. Sanity Check (Read Products)**

Verifies your API keys can authenticate and fetch the product list from Coinbase.

```powershell
docker compose -f docker/docker-compose.yml run --rm backend pytest tests/test_coinbase.py::test_coinbase_sanity_check -s
```

**2. Balance Check (Read Accounts)**

Confirms your keys have permission to read account balances. This is required for the bot to know how much capital is available.

```powershell
docker compose -f docker/docker-compose.yml run --rm backend pytest tests/test_coinbase.py::test_coinbase_balance_check -s
```

**3. Ticker Check (Read Price)**

Tests that the bot can fetch live prices for BTC-USD. This is the most frequently called API endpoint during operation.

```powershell
docker compose -f docker/docker-compose.yml run --rm backend pytest tests/test_coinbase.py::test_coinbase_ticker_check -s
```

If all three pass, your API keys are correctly configured and you're ready to enable live trading.

## Architecture

* **Backend:** Python (FastAPI)
* **Frontend:** React + Vite
* **Database:** PostgreSQL (Docker) / SQLite (Local dev)

See `SPEC.md` for detailed specifications and `SKILLS.md` for coding standards.
