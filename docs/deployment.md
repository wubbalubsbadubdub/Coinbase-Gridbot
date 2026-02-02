# Deployment Guide

This guide covers how to deploy the Coinbase Gridbot to a production environment (e.g., VPS, DigitalOcean Droplet, AWS EC2).

## Prerequisites
-   Docker & Docker Compose installed.
-   Coinbase Advanced Trade API Keys (Key and Secret).

## 1. Get Coinbase API Keys
1.  Log in to [Coinbase Advanced Trade](https://www.coinbase.com/advanced-trade).
2.  Go to **Settings > API**.
3.  Create a new API Key with **Trade** permissions (View, Transfer, Trade).
4.  **Important**: Save the `API Key Name` and `API Secret` immediately. You cannot see the secret again.

## 2. Server Setup
Clone the repository to your server:
```bash
git clone https://github.com/your-repo/coinbase-gridbot.git
cd coinbase-gridbot
```

## 3. Configuration
Create a `.env` file in the **`backend/`** directory:

```bash
# backend/.env
ENV=production
LOG_LEVEL=INFO

# Exchange Config
EXCHANGE_TYPE=coinbase
COINBASE_API_KEY=your_api_key_here
COINBASE_API_SECRET=your_api_secret_here

# Safety Settings
LIVE_TRADING_ENABLED=true   # Enable real trading
PAPER_MODE=false            # Disable paper trading
```

> **Warning**: Double-check `LIVE_TRADING_ENABLED=true` and `PAPER_MODE=false` before deploying. The bot defaults to paper trading mode for safety.

## 4. Run the Bot

**Linux/Mac:**
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

**Windows (PowerShell):**
```powershell
.\manage.ps1 dev
```

> **Note**: For production on Linux, consider using `docker compose` (v2) instead of `docker-compose` (v1).

## 5. Verification
1.  Open your browser and navigate to `http://YOUR_SERVER_IP:5173`.
2.  The Dashboard should load.
3.  Check **Bot Status** panel - Engine should show "RUNNING".
4.  Check **Trading Mode** - Should show "LIVE" (not "PAPER TRADING").
5.  Verify your API credentials work by checking if markets load with prices.

## 6. Maintenance

| Task | Command |
|------|---------|
| Stop the Bot | `docker compose -f docker/docker-compose.yml down` |
| View Logs | `docker compose -f docker/docker-compose.yml logs -f backend` |
| Update | `git pull && docker compose -f docker/docker-compose.yml up -d --build` |
| Run Tests | `docker compose -f docker/docker-compose.yml run --rm backend pytest` |

## 7. Windows Management Script (`manage.ps1`)
For Windows users, `manage.ps1` wraps common Docker commands for convenience.

| Command | Description |
| :--- | :--- |
| `.\manage.ps1 dev` | Start development environment |
| `.\manage.ps1 down` | Stop and remove containers |
| `.\manage.ps1 test` | Run backend unit tests |

## 8. Troubleshooting

**Bot not placing orders?**
- Check `LIVE_TRADING_ENABLED=true` in `backend/.env`
- Verify `PAPER_MODE=false`
- Ensure API keys have Trade permissions

**Can't connect to markets?**
- Check `EXCHANGE_TYPE=coinbase` (not `mock`)
- Verify API credentials are correct

**Frontend not loading?**
- Ensure port 5173 is open in your firewall
- Check frontend container logs: `docker compose -f docker/docker-compose.yml logs frontend`
