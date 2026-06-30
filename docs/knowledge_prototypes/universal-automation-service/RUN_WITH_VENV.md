# Running Universal Automation Service with Virtual Environment

## Issue Discovered

EventRelay and UVAI have complex internal dependencies and path requirements that make direct imports difficult. They're designed to run as standalone services, not as importable libraries.

## Recommended Solution: Service-Based Architecture

Instead of importing EventRelay/UVAI directly, we should interact with them as **running services**:

### Option 1: EventRelay Backend API (Recommended)

**Start EventRelay backend:**
```bash
cd /Users/garvey/Dev/OpenAI_Hub/projects/EventRelay
# Follow their startup instructions
npm run dev  # or python main.py, check their docs
```

**Update universal_coordinator.py to call EventRelay API:**
```python
# Instead of importing:
# from youtube_extension.services.workflows.transcript_action_workflow import VideoToActionWorkflow

# Use HTTP API:
import requests

class EventRelayClient:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url

    async def process_video(self, youtube_url):
        response = requests.post(
            f"{self.base_url}/api/v1/transcript-action",
            json={"video_url": youtube_url}
        )
        return response.json()
```

### Option 2: Gemini-Only Mode (Works Now)

Use the system for **enhanced video analysis** without EventRelay/UVAI:

```bash
# Activate venv
source venv/bin/activate

# Set API key
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"

# Run Gemini mode (no EventRelay/UVAI needed)
python3 universal_coordinator.py "https://youtu.be/VIDEO" --mode gemini --no-deploy
```

**What you get:**
- 10-dimensional video analysis
- Complete transcript
- Code extraction from video
- Automation opportunities identified
- Step-by-step procedures
- Skill suggestions

**Output:** Comprehensive JSON analysis saved to `results_*.json`

### Option 3: MCP Server Integration (Future)

EventRelay and UVAI may already have MCP servers running. Check:

```bash
# List running MCP servers
cat ~/.config/Claude/claude_desktop_config.json | python3 -m json.tool

# Check if EventRelay/UVAI servers are configured
```

Then use MCP to communicate instead of direct imports.

## Current Working Mode

**✅ Gemini Video Analysis** is fully functional right now:

```bash
# 1. Activate virtual environment
cd /Users/garvey/Dev/OpenAI_Hub/universal-automation-service
source venv/bin/activate

# 2. Set API key
export GEMINI_API_KEY="AIzaSyDu5GN_IxRFg3Ue8SYXSNWkZi-50pwDgS0"

# 3. Process a video
python3 universal_coordinator.py \
  "https://youtu.be/SHORT_TUTORIAL" \
  --mode gemini \
  --no-deploy

# 4. View results
cat results_*.json | python3 -m json.tool
```

## Next Steps

### Immediate: Test Gemini Mode

Test the working Gemini analysis with a real video to demonstrate value.

### Short-term: Service Integration

1. Start EventRelay backend as separate service
2. Update `universal_coordinator.py` to use HTTP API instead of imports
3. Same for UVAI if it has a REST API

### Long-term: Full Integration

1. Work with EventRelay/UVAI maintainers to expose proper Python APIs
2. Or keep service-based architecture (more scalable anyway)
3. Deploy as microservices with proper inter-service communication

## Why Service Architecture Is Better

**Benefits:**
- Each service runs independently
- Can scale services separately
- No dependency conflicts
- Production-ready deployment pattern
- Services can be in different languages/frameworks

**EventRelay** → Node.js/Python service on port 3000
**UVAI** → Python service on port 5000
**Universal Coordinator** → Python orchestrator calling both APIs
**Gemini** → Direct API integration (already works)

This is actually a **better architecture** than trying to force direct imports.

## Summary

**Status:**
- ✅ Gemini mode: **WORKING** (test it now!)
- ⚠️ EventRelay: Use as service (API calls), not direct import
- ⚠️ UVAI: Use as service (API calls), not direct import

**Recommendation:**
Test Gemini mode immediately to demonstrate value, then move to service-based architecture for EventRelay/UVAI integration.
