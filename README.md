# Project Odin v0.8.3

Project Odin is an AI-assisted market analysis and paper-trading application with
explainable, deterministic recommendations. The default interface is designed for
beginners, while technical tools remain available through Expert Mode.

## Current capabilities

- Beginner-focused market overview and plain-language explanations
- Technical analysis using EMA, RSI, MACD, and ATR
- Explainable multi-agent analysis with a transparent Chief AI decision
- Ranked market scanner
- Paper-trading account, positions, journal, and performance statistics
- Configurable automated paper-trading cycles
- Strategy registry and deterministic strategy evaluation
- Emergency controls and locked live trading

Project Odin currently supports paper trading only. News and macro agents remain
visibly offline until verified data sources are connected. Live trading remains
locked.

## Architecture

- React, TypeScript, and Vite frontend
- FastAPI backend
- PostgreSQL persistence with SQLAlchemy and Alembic
- Docker Compose development environment

The frontend uses a shared typed API layer with timeout, network, and invalid-response
handling. Backend unit tests use isolated FastAPI applications and dependency
overrides, so they do not require PostgreSQL, Docker, or external network access.

## Run with Docker

Create `.env` from `.env.example`, then run:

```powershell
docker compose up --build
```

Open `http://localhost:5173`.

## Development verification

Frontend:

```powershell
cd frontend
npm install
npm run format:check
npm run lint
npm run build
```

Backend:

```powershell
cd backend
python -m pip install -e ".[dev]"
python -m ruff format --check app tests
python -m ruff check app tests
python -m pytest -q
```

## Release history

- v0.8.3: isolated and stabilized the automated test suite
- v0.8.2: maintainability, shared UI, API robustness, and styling consistency
- v0.8.1: beginner-focused experience and simplified navigation
- v0.8.0: strategy registry and deterministic strategy evaluation
- v0.7.0: explainable multi-agent analysis engine

See [CHANGELOG.md](CHANGELOG.md) for detailed release notes.
