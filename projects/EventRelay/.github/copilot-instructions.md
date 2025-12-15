# GitHub Copilot Custom Instructions - EventRelay

## 🎯 Project Overview
EventRelay is an AI-powered agentic video execution platform that captures YouTube content, extracts events from transcripts, and dispatches intelligent agents to take real-world actions. The system combines FastAPI backend, React frontend, Gemini/Veo orchestration, and MCP/A2A agent workflows.

## 🔄 Core Workflow
**EventRelay has ONE and ONLY ONE workflow:**

1. **Paste YouTube Link** → User provides a YouTube URL
2. **Extract Context** → System transcribes video, extracts events from transcript
3. **Spawn Agents** → Intelligent agents are dispatched based on extracted events
4. **Run Tasks** → Agents execute real-world actions (create code, generate content, etc.)
5. **Publish Outputs** → Results are delivered through the dashboard and APIs

**⚠️ Important:** No other workflows, builders, or manual triggers exist. Everything starts with a YouTube link and flows automatically through the agent execution pipeline.

## 🏗️ Architecture Philosophy
- **Single-Flow Design**: One unified workflow from YouTube link to agent execution
- **MCP-First Design**: Model Context Protocol is the primary integration pattern
- **Agent-Driven**: Multi-agent coordination with specialized capabilities
- **Event-Sourced**: Video content drives agent execution and automatic dispatch
- **RAG-Enhanced**: All transcripts ground into knowledge store for continuous learning

## 📋 Core Principles

### Code Quality Standards
1. **Minimal Changes**: Make surgical, precise modifications - change as few lines as possible
2. **No Breaking Changes**: Never delete/remove working code unless fixing security issues
3. **Test Coverage**: Maintain >80% code coverage for new features
4. **Type Safety**: Use TypeScript strict mode for frontend, Python type hints for backend
5. **Error Handling**: Comprehensive error handling with proper logging

## 🚀 Quick Start Guide

### Initial Setup (First Time)

1. **Clone and setup Python environment:**
```bash
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .[dev,youtube,ml]
```

2. **Setup environment variables:**
```bash
cp .env.example .env
# Edit .env and add your API keys (see Environment Variables section below)
```

3. **Install frontend dependencies:**
```bash
npm install --prefix frontend
```

4. **Start backend server:**
```bash
uvicorn uvai.api.main:app --reload --port 8000
# Backend available at http://localhost:8000
# API docs at http://localhost:8000/docs
```

5. **Start frontend (in a new terminal):**
```bash
npm start --prefix frontend
# Frontend available at http://localhost:3000
```

### Development Workflow

**Working on Backend:**
```bash
# Activate virtual environment
source .venv/bin/activate

# Run backend
uvicorn uvai.api.main:app --reload --port 8000

# Run backend tests
pytest tests/ -v --cov

# Format code
black .
ruff check . --fix
```

**Working on Frontend:**
```bash
# Start dev server
npm start --prefix frontend

# Run tests
npm test --prefix frontend

# Build for production
npm run build --prefix frontend

# Lint and fix
npm run lint:fix --prefix frontend
```

**Working on Both (Full Stack):**
```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn uvai.api.main:app --reload --port 8000

# Terminal 2 - Frontend
npm start --prefix frontend

# Terminal 3 - Tests
pytest tests/ -v && npm test --prefix frontend
```

### Testing Standards
- **Default Test Video ID**: Always use `auJzb1D-fag` for ALL test data
- **NEVER** use `dQw4w9WgXcQ` (Rick Roll video) in test data
- Use real temporary directories, not mock filesystems (avoid pyfakefs)
- Clean up test files after completion with `tempfile` and `shutil`
- Run `pytest tests/` to verify before claiming completion

### File Organization
```
src/youtube_extension/   # Main Python package
frontend/               # React TypeScript application
development/agents/     # Agent implementations
tests/                 # All test files
docs/                  # Documentation (NOT root directory)
scripts/               # Utility scripts
```

## 🔧 Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **AI/ML**: Gemini API, OpenAI, Anthropic Claude
- **Video Processing**: Google Speech-to-Text v2, custom processors
- **MCP**: Model Context Protocol for agent communication
- **Database**: SQLite (development), PostgreSQL (production) via SQLAlchemy
- **Storage**: RAG store for transcript grounding

### Frontend
- **Framework**: React 18+ with TypeScript
- **State Management**: React hooks, context API
- **API Client**: Axios with retry logic
- **WebSocket**: Real-time communication support
- **Styling**: Modern CSS with component libraries
- **Build Tool**: React Scripts (Create React App)

### Backend-Frontend Integration
- **API Communication**: REST API via Axios from frontend to FastAPI backend
- **Default Ports**: Backend (8000), Frontend (3000)
- **CORS**: Configured in FastAPI to allow frontend origin
- **Environment Variables**: Backend uses `.env`, frontend uses `.env.development`

### Agent Framework
- **MCP Ecosystem**: Standardized agent communication
- **A2A Integration**: Agent-to-Agent workflows
- **Specialized Agents**: Code generator, video processor, metadata extractor
- **Orchestration**: Gemini Video Master Agent coordinates workflows

## 💻 Development Guidelines

### When Working with Python
```python
# Always use type hints
def process_video(video_url: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """Process video with comprehensive error handling."""
    try:
        # Implementation
        pass
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        raise
```

### When Working with TypeScript/React
```typescript
// Use strict TypeScript
interface VideoProcessingResult {
  result: any;
  status: 'success' | 'error';
  progress: number;
  timestamp: Date;
}

// Proper error handling
const processVideo = async (url: string): Promise<VideoProcessingResult> => {
  try {
    const response = await fetch(`${API_URL}/api/process-video`, {
      method: 'POST',
      body: JSON.stringify({ video_url: url })
    });
    return await response.json();
  } catch (error) {
    console.error('Video processing failed:', error);
    throw error;
  }
};
```

### When Working with MCP
- Use JSON-RPC 2.0 protocol for all communication
- Follow official MCP specification (2024-11-05)
- Implement proper error handling with error codes
- Include comprehensive logging for debugging
- Ensure AST-based code analysis for safety

## 🚫 Banned Practices

### CRITICAL - DO NOT DO THESE
1. ❌ Use `dQw4w9WgXcQ` as test video ID
2. ❌ Create loose Python files in project root
3. ❌ Use mock/fake filesystems (pyfakefs) for tests
4. ❌ Claim completion without running tests
5. ❌ Generate unnecessary .md file bloat
6. ❌ Commit secrets or API keys
7. ❌ Delete working code without justification
8. ❌ Break existing functionality
9. ❌ Create alternative workflows or manual builders
10. ❌ Add manual triggers that bypass the YouTube link flow
11. ❌ Build features that don't align with the single workflow pattern

## 🔐 Security Best Practices
1. **No Hardcoded Secrets**: Use environment variables
2. **Input Validation**: Validate all user inputs
3. **SQL Injection Prevention**: Use parameterized queries
4. **XSS Prevention**: Sanitize outputs
5. **OWASP Compliance**: Follow security guidelines
6. **MCP Context Isolation**: Prevent context leakage

## 🔑 Environment Variables

### Required Environment Variables

All environment variables should be configured in `.env` file (never commit this file).

#### Backend Environment Variables
```bash
# Core API Keys (REQUIRED)
YOUTUBE_API_KEY=your_youtube_api_key          # YouTube Data API v3
GEMINI_API_KEY=your_gemini_api_key            # Google Gemini API
OPENAI_API_KEY=your_openai_api_key            # OpenAI API (optional)
ANTHROPIC_API_KEY=your_anthropic_api_key      # Anthropic Claude (optional)
ASSEMBLYAI_API_KEY=your_assemblyai_api_key    # AssemblyAI (optional)

# Database Configuration (REQUIRED)
DATABASE_URL=sqlite:///./.runtime/app.db      # Development (SQLite)
# DATABASE_URL=postgresql://user:pass@host:5432/db  # Production (PostgreSQL)

# Google Cloud Speech-to-Text (for long videos)
GOOGLE_SPEECH_PROJECT_ID=your_project_id
GOOGLE_SPEECH_LOCATION=us-central1
GOOGLE_SPEECH_RECOGNIZER=transcript-recognizer
GOOGLE_SPEECH_GCS_BUCKET=your_gcs_bucket

# MCP Configuration
MCP_TIMEOUT=300
MCP_MAX_CONCURRENT=5
MCP_RETRY_ATTEMPTS=3
MCP_BATCH_SIZE=3
MCP_ENABLE_CIRCUIT_BREAKER=true

# Video Processing
VIDEO_PROCESSOR_TYPE=hybrid
CACHE_DIR=youtube_processed_videos/markdown_analysis
ENHANCED_ANALYSIS_DIR=youtube_processed_videos/enhanced_analysis

# Rate Limiting
RATE_LIMIT_RPS=5
MAX_RECENT_REQUESTS=1000

# Logging
LOG_LEVEL=INFO
REAL_MODE_ONLY=true
```

#### Frontend Environment Variables
```bash
# Frontend connects to backend API
REACT_APP_API_URL=http://localhost:8000      # Backend API URL
REACT_APP_WS_URL=ws://localhost:8000/ws      # WebSocket URL (optional)
```

### Environment Variable Usage Guidelines

**When working with backend code:**
- Always use `os.getenv()` or `pydantic-settings` to access environment variables
- Never hardcode API keys, database URLs, or secrets
- Provide sensible defaults for non-sensitive configuration
- Document all required environment variables in `.env.example`

**When working with frontend code:**
- Use `process.env.REACT_APP_*` to access environment variables
- All frontend environment variables must start with `REACT_APP_`
- Frontend environment variables are embedded at build time
- Never expose backend secrets in frontend code

**Example - Backend:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    youtube_api_key: str
    database_url: str = "sqlite:///./.runtime/app.db"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**Example - Frontend:**
```typescript
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const fetchVideoData = async (videoId: string) => {
  const response = await axios.get(`${API_URL}/api/v1/videos/${videoId}`);
  return response.data;
};
```

## 🔄 Backend-Frontend Compatibility

### API Contract Guidelines

**When modifying backend endpoints:**
1. **Version Your APIs**: Use `/api/v1/` prefix for stability
2. **Maintain Backward Compatibility**: Don't break existing endpoints
3. **Update Frontend Code**: Ensure frontend services are updated to match
4. **Document Changes**: Update API documentation at `/docs` endpoint
5. **Test Integration**: Verify frontend can consume the API changes

**When modifying frontend API calls:**
1. **Check Backend Contract**: Ensure endpoint exists and accepts your payload
2. **Handle Errors**: Implement proper error handling for API failures
3. **Type Safety**: Use TypeScript interfaces that match backend Pydantic models
4. **Environment Aware**: Use environment variables for API URLs

### Shared Data Models

Keep data models synchronized between backend and frontend:

**Backend (Pydantic):**
```python
from pydantic import BaseModel

class VideoProcessingRequest(BaseModel):
    video_url: str
    options: dict[str, Any] = {}

class VideoProcessingResponse(BaseModel):
    video_id: str
    status: str
    transcript: str | None
    events: list[dict[str, Any]]
```

**Frontend (TypeScript):**
```typescript
interface VideoProcessingRequest {
  video_url: string;
  options?: Record<string, any>;
}

interface VideoProcessingResponse {
  video_id: string;
  status: string;
  transcript?: string;
  events: Array<Record<string, any>>;
}
```

### Testing Backend-Frontend Integration

**Always test the full stack:**
1. Start backend: `uvicorn uvai.api.main:app --reload --port 8000`
2. Start frontend: `npm start --prefix frontend`
3. Test in browser: `http://localhost:3000`
4. Verify API calls in browser DevTools Network tab
5. Check backend logs for errors

**Common Integration Issues:**
- **CORS Errors**: Ensure FastAPI CORS middleware is configured correctly
- **Port Conflicts**: Check both services are running on expected ports
- **Environment Variables**: Verify all required variables are set
- **API URL Mismatch**: Confirm frontend is pointing to correct backend URL

## 💾 Database Connections

### Development Database (SQLite)
```python
# .env configuration
DATABASE_URL=sqlite:///./.runtime/app.db

# No additional setup required - SQLite file is created automatically
# Database file location: ./.runtime/app.db
```

### Production Database (PostgreSQL)
```python
# .env.production configuration
DATABASE_URL=postgresql://username:password@host:5432/database_name

# Required PostgreSQL environment variables:
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
POSTGRES_DB=eventrelay
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### Database Connection Best Practices

**When writing database code:**
1. **Use SQLAlchemy ORM**: Never write raw SQL queries
2. **Connection Pooling**: SQLAlchemy handles this automatically
3. **Migrations**: Use Alembic for schema changes
4. **Environment-Aware**: Use `DATABASE_URL` from environment variables
5. **Error Handling**: Wrap database operations in try-except blocks
6. **Connection Cleanup**: Use context managers or FastAPI dependencies

**Example - Database Session Management:**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./.runtime/app.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# FastAPI dependency
def get_db_dependency():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Database Migration Commands:**
```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# View migration history
alembic history
```

## 🎨 Code Style

### Python
- Use Black formatter with 88 character line length
- Follow PEP 8 conventions
- Use descriptive variable names
- Add docstrings to all public functions
- Group imports: standard library, third-party, local

### TypeScript
- Use Prettier with default settings
- Follow Airbnb style guide
- Prefer functional components with hooks
- Use meaningful component and prop names
- Extract reusable logic into custom hooks

## 📦 Common Commands

### Backend
```bash
# Install dependencies
pip install -e .[dev,youtube,ml]

# Run server
uvicorn uvai.api.main:app --reload --port 8000

# Run tests
pytest tests/ -v --cov

# Lint and format
ruff check . --fix
black .
mypy .
```

### Frontend
```bash
# Install dependencies
npm install --prefix frontend

# Run dev server
npm start --prefix frontend

# Run tests
npm test --prefix frontend

# Build production
npm run build --prefix frontend
```

## 🔍 Before Making Changes
1. Read and understand the CLAUDE.md governance file
2. Check `.claude/claude_instructions.md` for test data standards
3. Review `.cursor/rules/` for additional guidelines
4. Understand the complete context before suggesting changes
5. Verify changes don't break existing functionality

## 🎯 MCP Integration Patterns

### Core MCP Servers
EventRelay includes three core MCP servers for video processing:

1. **YouTube MCP Server** - Video metadata and transcript extraction
2. **YouTube Extension MCP Server** - Enhanced video processing
3. **Video Analysis MCP Server** - AI-powered video analysis

### Optional Developer Tools

#### GitHub MCP Server
The official GitHub MCP server enhances developer experience with AI-assisted GitHub operations:

**Installation:**
```json
// Add to .github/mcp-servers.json (already configured)
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@github/github-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

**Setup:**
1. Create GitHub Personal Access Token at https://github.com/settings/tokens
2. Select scopes: `repo`, `workflow`, `read:org`
3. Add to `.env`: `GITHUB_TOKEN=your_token`
4. Restart IDE to activate

**Capabilities:**
- AI-assisted code review and issue triage
- Automated PR creation and management
- CI/CD workflow debugging and log analysis
- Security vulnerability monitoring
- Project management automation

**Note:** This is a developer tool and not required for EventRelay's core workflow.

### Using MCP Tools
```python
# Example: Code analysis with MCP
from mcp import MCPClient

async def analyze_code(code: str) -> Dict[str, Any]:
    client = MCPClient()
    result = await client.call_tool(
        "code_analyzer",
        {"code": code, "language": "python"}
    )
    return result
```

### MCP Error Handling
```python
# Proper MCP error response
{
    "jsonrpc": "2.0",
    "error": {
        "code": -32600,  # Invalid Request
        "message": "Invalid parameters"
    },
    "id": "req_123"
}
```

## 📊 Performance Targets
- **API Response Time**: <200ms (p95)
- **Test Coverage**: >80%
- **Error Rate**: <0.1%
- **Build Time**: <2 minutes
- **Page Load**: <3 seconds

## 🔗 Key Resources
- MCP Protocol Spec: [2024-11-05 specification](https://modelcontextprotocol.io/docs)
- FastAPI Docs: https://fastapi.tiangolo.com
- React Docs: https://react.dev
- TypeScript: https://www.typescriptlang.org/docs
- GitHub Copilot Best Practices: https://gh.io/copilot-coding-agent-tips

### Evaluated Resources
These resources have been evaluated for potential integration into EventRelay. See `.github/RESOURCE_EVALUATION.md` for detailed analysis:

- **[langwatch/better-agents](https://github.com/langwatch/better-agents)** - CLI toolkit for reliable AI agent development with scenario testing and prompt versioning. *Status: Deferred for future enhancement.*
- **[github/github-mcp-server](https://github.com/github/github-mcp-server)** - Official GitHub MCP server for AI-assisted repository management. *Status: Integrated as optional developer tool.*
- **[Google Cloud agent-starter-pack](https://googlecloudplatform.github.io/agent-starter-pack/)** - Production-ready AI agent templates and infrastructure. *Status: Referenced for best practices only.*

## 🚀 Common Tasks

### Adding a New API Endpoint
All endpoints should support the core workflow: YouTube link → context extraction → agent dispatch.

1. Define Pydantic models in `backend/models/`
2. Create route handler in `backend/routers/`
3. Add tests in `tests/backend/`
4. Update API documentation
5. Add frontend integration in `frontend/src/services/`

### Adding a New Agent
Agents are spawned automatically as part of the workflow - never manually triggered.

1. Create agent class in `development/agents/specialized/`
2. Implement MCP protocol handlers
3. Add agent registration in coordinator
4. Create comprehensive tests
5. Document agent capabilities

### Processing a Video
This is the core workflow - all features should enhance this flow.

1. Accept YouTube URL from user input
2. Use unified video processor factory
3. Delegate to appropriate specialized processor
4. Extract events from transcript
5. Automatically spawn and dispatch agents based on events
6. Cache results for performance
7. Update RAG store with transcript

## 💡 Tips for Success
1. **Read First, Code Second**: Understand existing patterns before implementing
2. **Test Early, Test Often**: Write tests alongside code
3. **Small Commits**: Make incremental, reviewable changes
4. **Clear Names**: Use descriptive variable and function names
5. **Document Why**: Comments should explain why, not what
6. **Performance Matters**: Consider scalability in design decisions
7. **Security First**: Always validate inputs and sanitize outputs
8. **Environment Variables**: Never hardcode secrets or configuration
9. **Test Full Stack**: Always test backend and frontend integration together
10. **Check Compatibility**: Verify backend changes don't break frontend

## 🐛 Common Troubleshooting

### Backend Issues

**ModuleNotFoundError:**
```bash
# Ensure virtual environment is activated and dependencies installed
source .venv/bin/activate
pip install -e .[dev,youtube,ml]
```

**Database Connection Errors:**
```bash
# Check DATABASE_URL is set correctly
echo $DATABASE_URL

# For SQLite, ensure directory exists
mkdir -p .runtime

# For PostgreSQL, verify connection
python -c "from sqlalchemy import create_engine; engine = create_engine('$DATABASE_URL'); engine.connect()"
```

**Missing API Keys:**
```bash
# Verify environment variables are loaded
python -c "import os; print(os.getenv('YOUTUBE_API_KEY'))"

# Check .env file exists and has correct format
cat .env | grep -v "^#" | grep -v "^$"
```

### Frontend Issues

**Build Errors:**
```bash
# Clear cache and reinstall
rm -rf frontend/node_modules frontend/package-lock.json
npm install --prefix frontend

# Increase memory for large builds
export NODE_OPTIONS="--max-old-space-size=8192"
npm run build --prefix frontend
```

**API Connection Errors:**
```bash
# Verify REACT_APP_API_URL is set
echo $REACT_APP_API_URL

# Check backend is running
curl http://localhost:8000/health

# Test CORS configuration
curl -H "Origin: http://localhost:3000" -I http://localhost:8000/api/v1/
```

**TypeScript Errors:**
```bash
# Regenerate types
npm run build --prefix frontend

# Check TypeScript configuration
npx tsc --showConfig --prefix frontend
```

### Integration Issues

**CORS Errors in Browser:**
1. Verify FastAPI CORS middleware is configured for frontend origin
2. Check backend logs for CORS-related errors
3. Ensure frontend is using correct API URL from environment variables

**API 404 Errors:**
1. Verify backend endpoint exists: Check `/docs` at `http://localhost:8000/docs`
2. Confirm frontend is calling correct URL path
3. Check for typos in endpoint paths

**Environment Variable Not Working:**
1. Backend: Restart uvicorn after changing `.env`
2. Frontend: Restart `npm start` after changing `.env.development`
3. Verify variable name format (frontend must use `REACT_APP_` prefix)

**Database Migration Issues:**
```bash
# Reset database (development only)
rm .runtime/app.db
alembic upgrade head

# Check migration status
alembic current
alembic history
```

## 🎓 Learning Path
For new contributors:
1. Review README.md for setup instructions
2. Read docs/CLAUDE.md for architecture
3. Explore example workflows in `examples/`
4. Review test files to understand patterns
5. Start with small bug fixes before features

## 🔄 Continuous Improvement
This is a living document. The project evolves with:
- New MCP capabilities
- Enhanced agent workflows
- Improved video processing
- Better user experiences
- Stronger security measures

Always prioritize code quality, security, and user value in your contributions.
