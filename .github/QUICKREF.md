# Copilot Quick Reference - EventRelay

## 🚀 Quick Commands

### Start Development
```bash
# Activate environment
source .venv/bin/activate

# Run backend
uvicorn uvai.api.main:app --reload --port 8000

# Run frontend (new terminal)
npm start --prefix frontend

# Run tests
pytest tests/ -v --cov
```

### Code Quality
```bash
# Format Python
black . && ruff check . --fix

# Format TypeScript
npm run format --prefix frontend

# Type check
mypy . && npm run type-check --prefix frontend
```

## 🎯 Key Patterns

### Always Use Test Video ID
```python
# ✅ Correct
TEST_VIDEO_ID = "auJzb1D-fag"

# ❌ Never use
BANNED_VIDEO_ID = "dQw4w9WgXcQ"  # Rick Roll
```

### API Endpoint Pattern
```python
@app.post("/api/v1/my-endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    """Clear docstring explaining what this does."""
    try:
        # Implementation
        return MyResponse(status="success", data=result)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

### Frontend API Call Pattern
```typescript
const fetchData = async (): Promise<ApiResponse> => {
  try {
    const response = await fetch(`${API_URL}/api/endpoint`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return await response.json();
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
};
```

### MCP Tool Usage
```python
from mcp import MCPClient

async def analyze_code(code: str) -> dict:
    client = MCPClient()
    return await client.call_tool(
        "code_analyzer",
        {"code": code, "language": "python"}
    )
```

## 🚫 Never Do This

1. ❌ Hardcode secrets or API keys
2. ❌ Use banned test video ID
3. ❌ Create files in project root (use src/, tests/, etc.)
4. ❌ Delete working code without justification
5. ❌ Skip tests before claiming completion
6. ❌ Use mock filesystems (use real temp dirs)

## ✅ Always Do This

1. ✅ Use type hints (Python) and strict types (TypeScript)
2. ✅ Add comprehensive error handling
3. ✅ Write/update tests for new features
4. ✅ Use environment variables for config
5. ✅ Clean up temporary test files
6. ✅ Follow existing project patterns

## 📚 Quick Links

- **Setup Guide**: `.github/COPILOT_SETUP.md`
- **Full Instructions**: `.github/copilot-instructions.md`
- **MCP Docs**: `.github/mcp-config.md`
- **Architecture**: `docs/CLAUDE.md`
- **API Docs**: http://localhost:8000/docs

## 💬 Copilot Chat Examples

```
# Get project-specific help
@workspace How do I add a new video processor?
@workspace What's the correct pattern for error handling?
@workspace Show me examples of MCP server usage

# Code generation with context
# In your code, add comment:
# Create an API endpoint for video analysis using Gemini
```

## 🔍 Common File Locations

```
src/youtube_extension/        # Main Python package
  ├── backend/               # FastAPI routers
  ├── services/              # Business logic
  ├── integrations/          # External API integrations
  └── mcp/                   # MCP implementations

frontend/src/                 # React application
  ├── components/            # UI components
  ├── services/              # API clients
  └── hooks/                 # Custom React hooks

development/agents/           # Agent implementations
tests/                       # All test files
docs/                        # Documentation
scripts/                     # Utility scripts
```

## 🎨 Code Style

### Python
- Line length: 88 characters (Black default)
- Imports: stdlib, third-party, local
- Docstrings: Google style
- Type hints: Required for public functions

### TypeScript
- Line length: 80 characters (Prettier default)
- Prefer functional components with hooks
- Use meaningful names
- Extract complex logic to custom hooks

## 🧪 Testing Standards

```python
# Use real temp directories
import tempfile
import shutil

def test_video_processing():
    temp_dir = tempfile.mkdtemp()
    try:
        # Test code here
        result = process_video("auJzb1D-fag")
        assert result.status == "success"
    finally:
        shutil.rmtree(temp_dir)
```

## 🔐 Environment Variables

Copy from `.env.example` and set:
```bash
YOUTUBE_API_KEY=        # Required
GEMINI_API_KEY=         # Required
OPENAI_API_KEY=         # Optional
MCP_TIMEOUT=300
MCP_MAX_CONCURRENT=5
```

## 📊 Performance Targets

- API Response: <200ms (p95)
- Test Coverage: >80%
- Error Rate: <0.1%
- Build Time: <2 minutes

---

**Need more details?** See `.github/COPILOT_SETUP.md` for complete setup guide.
