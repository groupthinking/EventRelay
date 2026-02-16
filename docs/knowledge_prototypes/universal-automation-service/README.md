# Universal Automation Service - YouTube to Skills Pipeline

**Input:** YouTube URL → **Output:** Automated workflows, skills, and executions

## 🎯 Architecture Overview

```
YouTube URL
    ↓
EventRelay Processing (9 MCP Servers)
    ├── youtube_api_proxy.py - Video metadata & API handling
    ├── transcription_mcp_server.py - Audio → Text transcription
    ├── video_analysis_mcp_server.py - Content intelligence
    └── learning_analytics_mcp_server.py - Pattern extraction
    ↓
UVAI Intelligence Layer
    ├── context7_mcp.py - Context management & cross-system awareness
    ├── infrastructure_packaging_mcp.py - Infrastructure planning
    └── UVAI Agents (26+ specialized processors)
    ↓
Self-Correcting Executor
    ├── Skill creation automation
    ├── Workflow execution with retry logic
    ├── Error detection & auto-repair
    └── Performance monitoring
    ↓
OUTPUT: Claude Code Skills + Automated Workflows
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+ (for monitoring dashboard)
- YouTube API key (optional, fallback available)
- All dependencies from EventRelay, UVAI, and Executor

### Installation

```bash
cd /Users/garvey/Dev/OpenAI_Hub/universal-automation-service

# Install Python dependencies
pip3 install -r requirements.txt

# Setup MCP servers (optional)
python3 setup_mcp_config.py
```

### Basic Usage

```bash
# Process a YouTube URL
python3 coordinator.py "https://www.youtube.com/watch?v=VIDEO_ID"

# With monitoring
python3 coordinator.py "https://www.youtube.com/watch?v=VIDEO_ID" --monitor
```

## 🧑‍💻 Contributor Guide
Shared contribution standards, module layout, and testing practices for the EventRelay pipeline live in [Repository Guidelines](../../../AGENTS.md). Review it before opening PRs to ensure MCP, monitor, and client changes stay consistent.

## 📊 Pipeline Components

### 1. Coordinator (`coordinator.py`)
**Main orchestrator** that manages the entire pipeline flow.

- Validates YouTube URLs
- Routes through EventRelay → UVAI → Executor
- Tracks pipeline state and errors
- Returns final automation output

**Usage:**
```python
from coordinator import UniversalAutomationCoordinator

coordinator = UniversalAutomationCoordinator()
result = coordinator.process_youtube_url("https://youtube.com/watch?v=...")
```

### 2. EventRelay Integration (`youtube_ingestion.py`)
**Video processing layer** connecting to 9 EventRelay MCP servers.

**Pipeline Steps:**
1. Fetch video metadata (youtube_api_proxy)
2. Extract transcript (transcription_mcp_server)
3. Analyze content (video_analysis_mcp_server)
4. Extract learning patterns (learning_analytics_mcp_server)

**Output:** Structured video data with metadata, transcript, analysis, and patterns.

### 3. UVAI Intelligence (`uvai_intelligence.py`)
**Intelligence layer** that processes EventRelay data into actionable insights.

**Processing Steps:**
1. Create context session (context7_mcp)
2. Extract automation opportunities
3. Generate skill requirements
4. Build infrastructure plan (infrastructure_packaging_mcp)

**Output:** Intelligence data with automation opportunities, skill specs, and action plans.

### 4. Self-Correcting Executor (`executor_action.py`)
**Execution layer** that creates skills and runs workflows with auto-repair.

**Execution Flow:**
1. Parse infrastructure plan
2. Create Claude Code skills
3. Execute workflows with retry logic
4. Apply self-correction on errors
5. Generate final output

**Output:** Created skills, execution logs, and automation results.

## 🔧 Configuration

### MCP Server Configuration
**File:** `config/mcp_servers.json`

Defines all MCP servers used in the pipeline:
- EventRelay servers (youtube-api-proxy, transcription, video-analysis, learning-analytics)
- UVAI servers (context7, infrastructure-packaging)
- Executor server (self-correcting-executor)

### Pipeline Configuration
**File:** `config/pipeline_config.json`

Controls pipeline behavior:
- Stage timeouts and retry attempts
- Output directories (skills, logs, events)
- Monitoring settings
- Feature flags

## 📈 Monitoring & Visualization

### Real-Time Dashboard
**Location:** `monitoring/dashboard.py`

Features:
- Live pipeline progress tracking
- YouTube URL input form
- EventRelay → UVAI → Executor stage visualization
- Event feed with WebSocket updates
- Mermaid workflow diagrams

**Start Dashboard:**
```bash
cd monitoring
npm start
# Opens http://localhost:3000
```

### Event Logging
All pipeline events logged to: `events/pipeline-events.jsonl`

Event types:
- `pipeline.started` - New YouTube URL processing started
- `eventrelay.completed` - Video processing finished
- `uvai.intelligence.generated` - Intelligence extraction complete
- `executor.skill.created` - New skill created
- `pipeline.completed` - Full pipeline finished

## 🎓 Example Workflow

```bash
# 1. Start monitoring dashboard
cd monitoring && npm start &

# 2. Process YouTube video about "Python automation"
python3 coordinator.py "https://youtube.com/watch?v=automation-tutorial"

# Pipeline executes:
# - EventRelay fetches video + transcript
# - UVAI analyzes content → identifies "Python automation" patterns
# - Executor creates skill: "python-automation.md" in ~/.claude/skills/
# - Skill auto-invoked when Claude detects Python automation tasks
```

**Result:** Claude Code now has a custom skill for Python automation, extracted from the YouTube video content.

## 🔄 Codex + Claude Coordination

This service is designed for **multi-agent environments** with both Codex and Claude terminal sessions active.

### Coordination Features:
- Shared event logging (both agents see pipeline progress)
- MCP server coordination (prevents conflicts)
- Skill creation visible to both agents
- Real-time dashboard shows all agent activity

### Usage in Multi-Agent Mode:
```bash
# Terminal 1 (Codex)
codex run --agent youtube-processor

# Terminal 2 (Claude)
claude run coordinator.py "https://youtube.com/..."

# Both agents coordinate through MCP servers and shared event log
```

## 📂 Project Structure

```
universal-automation-service/
├── coordinator.py              # Main orchestrator
├── youtube_ingestion.py        # EventRelay integration
├── uvai_intelligence.py        # UVAI processing
├── executor_action.py          # Self-correcting executor interface
├── config/
│   ├── mcp_servers.json       # MCP server configurations
│   └── pipeline_config.json   # Pipeline settings
├── monitoring/
│   ├── dashboard.py           # Real-time monitoring dashboard
│   ├── server.js              # WebSocket server
│   └── public/index.html      # Dashboard UI
├── events/
│   └── pipeline-events.jsonl  # Event log
├── logs/
│   └── pipeline.log           # Execution logs
└── README.md                   # This file
```

## 🧪 Testing

### Test Individual Components

```bash
# Test EventRelay integration
python3 youtube_ingestion.py "VIDEO_ID"

# Test UVAI intelligence (requires EventRelay output)
python3 uvai_intelligence.py

# Test executor (requires UVAI output)
python3 executor_action.py
```

### End-to-End Test

```bash
# Full pipeline test
python3 coordinator.py "https://youtube.com/watch?v=test-video" --test

# With verbose logging
python3 coordinator.py "https://youtube.com/watch?v=test-video" --verbose
```

## 🐛 Troubleshooting

### MCP Server Connection Issues
```bash
# Check MCP server status
python3 -c "from coordinator import UniversalAutomationCoordinator; c = UniversalAutomationCoordinator(); print(c.check_mcp_servers())"

# Restart MCP servers
python3 setup_mcp_config.py --restart
```

### Missing API Keys
Some EventRelay servers require API keys. Check `config/mcp_servers.json` and set environment variables:

```bash
export YOUTUBE_API_KEY="your-key-here"
export YOUTUBE_EXTENSION_BASE="http://localhost:8000"
```

### Skill Creation Failures
Skills are created in `~/.claude/skills/`. Verify directory permissions:

```bash
mkdir -p ~/.claude/skills
chmod 755 ~/.claude/skills
```

## 🎯 Integration Points

### EventRelay MCP Servers
**Location:** `/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/external/mcp_servers/`

9 servers providing video processing capabilities.

### UVAI Ecosystem
**Location:** `/Users/garvey/Dev/OpenAI_Hub/projects/UVAI/`

29 MCP ecosystem servers, 26 agents, intelligence infrastructure.

### Self-Correcting Executor
**Location:** `/Users/garvey/self-correcting-executor-PRODUCTION/mcp_server/`

Production-ready execution framework with auto-repair.

## 🚧 Development Roadmap

- [x] Core pipeline implementation (EventRelay → UVAI → Executor)
- [x] MCP server configuration
- [x] Basic monitoring dashboard
- [ ] Advanced workflow visualization
- [ ] User adjustment interface (Phase 4)
- [ ] Automated skill testing
- [ ] Performance analytics
- [ ] Multi-video batch processing

## 📝 Notes

- **Demo Mode:** EventRelay servers have fallback responses if YouTube Extension backend is offline
- **Self-Correction:** Executor retries failed phases up to 3 times with correction logic
- **Event Logging:** All pipeline events logged to JSONL for audit trail
- **Skills Auto-Invocation:** Created skills are automatically invoked by Claude based on task context

---

**Built with the UVAI Ecosystem principles:**
- No mocks, only real working code
- Event-driven architecture
- Self-correcting execution
- Measurable outcomes
- Multi-agent coordination

**Status:** ✅ Core pipeline functional, ready for YouTube URL → Skills automation
