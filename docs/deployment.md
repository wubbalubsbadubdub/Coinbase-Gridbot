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
Create a `.env` file in the root directory (or rename `.env.example`):

```bash
# .env
ENV=production
LOG_LEVEL=INFO

# Exchange Config
EXCHANGE_TYPE=coinbase
COINBASE_API_KEY=your_api_key_here
COINBASE_API_SECRET=your_api_secret_here

# Safety
LIVE_TRADING_ENABLED=true
```

## 4. Run the Bot
Use the provided PowerShell script (Windows) or Docker Compose directly (Linux):

**Linux:**
```bash
docker-compose up -d --build
```

**Windows:**
```powershell
.\manage.ps1 dev
```

## 5. Verification
1.  Open your browser and navigate to `http://YOUR_SERVER_IP:5173`.
2.  The Dashboard should load.
3.  Check the **Status Pill** in the top left. It should say "RUNNING".
4.  Markets with active trading should show "Live".

## 6. Maintenance
-   **Stop the Bot**: `docker-compose down`
-   **View Logs**: `docker-compose logs -f backend`
-   **Update**: `git pull && docker-compose up -d --build`

## 7. Windows Management Script (`manage.ps1`)
For Windows users, `manage.ps1` wraps common Docker commands for convenience.

| Command | Description | Underlying Docker Command |
| :--- | :--- | :--- |
| `.\manage.ps1 dev` | **Start System**: Builds and runs services in background (with logs). | `docker-compose up --build` |
| `.\manage.ps1 down` | **Stop System**: Stops and removes containers. | `docker-compose down` |
| `.\manage.ps1 test` | **Run Tests**: Executes backend unit tests (pytest). | `docker-compose run backend pytest` |

