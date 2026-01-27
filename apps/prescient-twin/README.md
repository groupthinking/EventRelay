# Prescient Twin

Self-evolving agent architecture with hybrid model routing.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Copy environment template
cp .env.example .env
# Edit .env with your API keys

# 3. Run interactive mode
uv run python ecosystem.py --interactive

# 4. Or start the API server
uv run python main.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESCIENT TWIN                           │
├─────────────────────────────────────────────────────────────┤
│  FastAPI Server (main.py)                                   │
│  └── /evolve, /execute, /stats, /health                    │
├─────────────────────────────────────────────────────────────┤
│  Hybrid Router (router.py)                                  │
│  └── Gemini (Visual) | Claude (Code) | Grok (Realtime)     │
├─────────────────────────────────────────────────────────────┤
│  Sandbox (sandbox_tool.py)    │   Memory (memory.py)        │
│  └── E2B Remote Execution     │   └── Tool Repository       │
└─────────────────────────────────────────────────────────────┘
```

## Endpoints

| Endpoint   | Method | Description                 |
| ---------- | ------ | --------------------------- |
| `/health`  | GET    | Health check                |
| `/stats`   | GET    | System statistics           |
| `/evolve`  | POST   | Route task to best AI brain |
| `/execute` | POST   | Execute code in sandbox     |
| `/tools`   | GET    | List evolved tools          |

## Production (PM2)

```bash
# Install PM2
npm install -g pm2

# Start with PM2
pm2 start ecosystem.py --interpreter $(uv python find) --name "prescient-twin"

# Make persistent
pm2 save
pm2 startup
```
