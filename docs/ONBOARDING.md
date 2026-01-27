# EventRelay Contributor Onboarding Guide

> Everything you need to go from zero to contributing in under 30 minutes.

---

## TL;DR Setup

```bash
# 1. Clone and setup
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay
python -m venv .venv && source .venv/bin/activate
pip install -e .[dev,youtube,ml]
npm install --prefix apps/web

# 2. Configure (interactive)
python3 scripts/setup_env.py

# 3. Run
uvicorn uvai.api.main:app --reload --port 8000  # Backend
npm start --prefix apps/web                      # Frontend (separate terminal)

# 4. Verify
open http://localhost:8000/docs  # API docs
open http://localhost:3000       # Dashboard
```

---

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.9+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 8+ | `npm --version` |
| Git | Any | `git --version` |

**API Keys (need at least one):**
- [Google AI Studio](https://aistudio.google.com/app/apikey) → `GEMINI_API_KEY`
- [OpenAI Platform](https://platform.openai.com/api-keys) → `OPENAI_API_KEY`

---

## Step 1: Environment Setup

### Option A: Interactive Setup (Recommended)

```bash
python3 scripts/setup_env.py
```

This wizard will:
- Create `.env` from template
- Prompt for each API key with help URLs
- Validate your configuration
- Show exactly what's missing

### Option B: Manual Setup

```bash
cp .env.example .env
# Edit .env and add your keys
```

**Minimum Required:**
```bash
# Pick at least one AI provider
GEMINI_API_KEY=your-key-here
# OR
OPENAI_API_KEY=your-key-here
```

**Recommended Additions:**
```bash
YOUTUBE_API_KEY=your-key      # Better video metadata
ANTHROPIC_API_KEY=your-key    # Claude support
```

### Validate Configuration

```bash
python3 scripts/validate_env.py
```

You should see:
```
✓ GEMINI_API_KEY configured
✓ Required dependencies installed
✓ Database connection successful
```

---

## Step 2: Running the Application

### Backend (Terminal 1)

```bash
uvicorn uvai.api.main:app --reload --port 8000
```

Or using the CLI:
```bash
youtube-extension serve --host 0.0.0.0 --port 8000
```

**Verify:** http://localhost:8000/docs should show Swagger UI.

### Frontend (Terminal 2)

```bash
npm start --prefix apps/web
```

Or:
```bash
npm run dev --prefix apps/web
```

**Verify:** http://localhost:3000 should show the dashboard.

### Database (Optional - for PostgreSQL)

```bash
cd supabase
docker-compose up -d
```

This starts PostgreSQL on port 5432 (credentials: postgres/postgres).

---

## Step 3: Make Your First Change

### Quick Test: Add a Log Statement

1. Open `src/youtube_extension/backend/api/v1/router.py`
2. Find the `health_check_v1` function
3. Add a log statement:
   ```python
   @router.get("/health")
   async def health_check_v1():
       print("Health check called!")  # Your addition
       return {"status": "healthy"}
   ```
4. Save the file (auto-reload kicks in)
5. Visit http://localhost:8000/health
6. Check your terminal - you should see the log

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/unit/test_agent_gap_analyzer.py -v

# With coverage
pytest tests/ --cov=src/youtube_extension --cov-report=html
```

### Linting & Formatting

```bash
# Lint
youtube-extension lint
# Or directly
ruff check src --ignore E402,F811,F401,F821

# Format
youtube-extension format
# Or
black src/
isort src/
```

---

## Step 4: Understanding the Codebase

### Key Directories

| Directory | What's There |
|-----------|--------------|
| `src/youtube_extension/backend/` | FastAPI app, routes, services |
| `src/youtube_extension/services/agents/` | Agent orchestration |
| `src/agents/` | Standalone agents |
| `apps/web/` | Next.js frontend |
| `mcp-servers/` | MCP server implementations |
| `scripts/` | Utility scripts |
| `tests/` | Test suite |

### Entry Points

| File | Purpose |
|------|---------|
| `src/youtube_extension/backend/main.py` | FastAPI app creation |
| `src/youtube_extension/backend/api/v1/router.py` | REST endpoints |
| `apps/web/src/app/page.tsx` | Frontend home page |
| `prescient-twin/main.py` | Self-evolving agent server |

### How Things Connect

```
User Request
    ↓
router.py (validates request)
    ↓
service_container.py (gets service)
    ↓
video_processing_service.py (business logic)
    ↓
agent_orchestrator.py (dispatches agents)
    ↓
agents/*.py (executes tasks)
```

---

## Step 5: Development Workflow

### Creating a Feature Branch

```bash
git checkout -b feature/my-awesome-feature
```

### Development Cycle

1. **Write code** (with type hints!)
2. **Run linter:** `youtube-extension lint`
3. **Run tests:** `pytest tests/ -v`
4. **Test manually:** Check the Swagger UI or frontend

### Committing

```bash
git add <specific files>
git commit -m "Add: Brief description of what you did"
```

**Commit Message Format:**
- `Add:` New feature
- `Fix:` Bug fix
- `Update:` Enhance existing feature
- `Refactor:` Code cleanup
- `Docs:` Documentation only

### Pull Request Checklist

Before opening a PR, verify:
- [ ] Linting passes: `youtube-extension lint`
- [ ] Tests pass: `pytest tests/ -v`
- [ ] New code has type hints
- [ ] Complex functions have docstrings
- [ ] No secrets committed (check `.env` is in `.gitignore`)

---

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic models in `src/youtube_extension/backend/api/v1/models.py`:
   ```python
   class MyRequest(BaseModel):
       video_url: str
       option: Optional[str] = None

   class MyResponse(BaseModel):
       result: str
       success: bool
   ```

2. Add endpoint in `router.py`:
   ```python
   @router.post("/my-endpoint", response_model=MyResponse)
   async def my_endpoint(
       request: MyRequest,
       video_service: VideoProcessingService = Depends(get_video_processing_service)
   ):
       result = await video_service.do_something(request.video_url)
       return MyResponse(result=result, success=True)
   ```

3. Add test in `tests/unit/test_my_feature.py`:
   ```python
   def test_my_endpoint():
       response = client.post("/api/v1/my-endpoint", json={"video_url": "..."})
       assert response.status_code == 200
   ```

### Adding a New Agent

1. Create agent in `src/agents/specialized/my_agent.py`:
   ```python
   from src.youtube_extension.services.agents.base_agent import BaseAgent

   class MyAgent(BaseAgent):
       def __init__(self):
           super().__init__(name="MyAgent", role="Does cool stuff")

       async def execute(self, inputs: dict) -> dict:
           # Your logic here
           return {"result": "done"}
   ```

2. Register in agent config (`config/agent_network.json`)

3. Add tests

### Adding a New Service

1. Create service in `src/youtube_extension/backend/services/my_service.py`:
   ```python
   class MyService:
       def __init__(self, dependencies):
           self.deps = dependencies

       async def do_thing(self, input: str) -> str:
           return f"Processed: {input}"
   ```

2. Register in service container (`containers/service_container.py`)

3. Create dependency function:
   ```python
   def get_my_service() -> MyService:
       return get_service('my_service')
   ```

---

## Debugging Tips

### Common Issues

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Activate venv: `source .venv/bin/activate` |
| Port 8000 in use | `lsof -i :8000` then kill the process |
| API key errors | Run `python3 scripts/validate_env.py` |
| Import errors | `pip install -e .[dev,youtube,ml]` |
| Frontend won't start | `rm -rf node_modules && npm install --prefix apps/web` |

### Debugging Backend

Add breakpoints or use the VS Code debugger:

```json
// .vscode/launch.json
{
  "configurations": [
    {
      "name": "FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["uvai.api.main:app", "--reload", "--port", "8000"]
    }
  ]
}
```

### Checking Logs

```bash
# Backend logs appear in terminal running uvicorn
# Or check log files
tail -f logs/app.log
```

---

## Dev Container (Optional)

If you use VS Code with Docker:

1. Install "Dev Containers" extension
2. Open command palette: `Dev Containers: Reopen in Container`
3. Wait for container to build
4. You're ready - ports auto-forward

The container includes:
- Python 3.9+
- Node.js 18+
- GitHub CLI
- All recommended VS Code extensions

---

## Mandatory Policies

### REAL_MODE_ONLY Enforcement

In production, `REAL_MODE_ONLY=true` enforces:
- No simulated delays (`asyncio.sleep` for fake waits)
- No hardcoded mock responses
- All code must be production-ready

**Violations of this policy may result in PR rejection.**

### Security Standards

- Never commit `.env` or secrets
- Validate all user inputs
- Avoid `dangerouslySetInnerHTML` in React
- Use subprocess safely (sanitize inputs)

### Code Quality

- Python: Type hints required, follow Black/Ruff formatting
- TypeScript: Strict mode, no `any` types
- All new functions need docstrings
- Tests required for new features

---

## Getting Help

1. **Check existing docs:**
   - `README.md` - Overview
   - `AGENTS.md` - Agent development
   - `docs/MASTER_IMPLEMENTATION_GUIDE.md` - Deep dive

2. **Search existing code:**
   ```bash
   grep -r "something" src/
   ```

3. **Check tests for examples:**
   ```bash
   ls tests/unit/
   ```

4. **File an issue** on GitHub with:
   - What you're trying to do
   - What's not working
   - Error messages

---

## What to Work On

### Good First Issues

Look for issues labeled `good-first-issue` on GitHub. These are typically:
- Documentation improvements
- Adding tests for existing code
- Small bug fixes
- Improving error messages

### Areas That Need Help

Based on codebase analysis:
- Frontend-backend integration (connecting dashboard to API)
- Test coverage expansion
- API documentation
- MCP server implementations

---

## Quick Reference Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev,youtube,ml]
npm install --prefix apps/web
python3 scripts/setup_env.py

# Run
uvicorn uvai.api.main:app --reload --port 8000
npm start --prefix apps/web

# Test
pytest tests/ -v
pytest tests/ --cov=src/youtube_extension

# Lint
youtube-extension lint
youtube-extension format

# Validate
python3 scripts/validate_env.py
curl http://localhost:8000/health
```

---

Welcome to EventRelay! We're excited to have you contributing. 🚀
