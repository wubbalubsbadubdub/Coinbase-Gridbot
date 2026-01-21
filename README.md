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

## Architecture

* **Backend:** Python (FastAPI)
* **Frontend:** React + Vite
* **Database:** PostgreSQL (Docker) / SQLite (Local dev)

See `SPEC.md` for detailed specifications and `SKILLS.md` for coding standards.
