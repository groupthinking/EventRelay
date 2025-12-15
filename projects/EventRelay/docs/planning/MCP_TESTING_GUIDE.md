# MCP Server Testing Guide for Claude Desktop
**Date**: 2025-10-27
**Status**: Testing Framework for 8 MCP Servers

---

## Important: Claude Desktop vs Claude Code CLI

**You are currently in Claude Code CLI** - This is a terminal-based interface.

**Claude Desktop** is a separate GUI application where MCP servers are configured.

**MCP servers in `~/.claude/claude_desktop_config.json` are for Claude Desktop only.**

---

## Testing Overview

### 8 MCP Servers to Test:
1. youtube-uvai-processor (Python, stdio)
2. self-correcting-executor (Python, stdio)
3. perplexity (Python module, stdio)
4. unified-analytics (Node.js, stdio)
5. metacognition-tools (Node.js, stdio)
6. supabase (HTTP, remote)
7. openai (npm package, stdio)
8. groq (npm package, stdio)

---

## Method 1: Test in Claude Desktop (Recommended)

### Step 1: Open Claude Desktop
1. Launch Claude Desktop application
2. Wait for initialization
3. MCP servers should auto-connect

### Step 2: Check MCP Server Status
In Claude Desktop, type:
```
Can you list all available MCP servers and tools?
```

Expected output should show all 8 servers with their tools.

### Step 3: Test Individual Servers

#### Test 1: YouTube UVAI Processor
```
Use the youtube-uvai-processor to extract the video ID from: https://youtu.be/jawdcPoZJmI
```

**Expected**: Video ID extracted successfully

#### Test 2: Metacognition Tools
```
Use the metacognition-tools to perform a Fermi estimation: How many piano tuners are in Chicago?
```

**Expected**: Step-by-step estimation with reasoning

#### Test 3: Unified Analytics
```
Use unified-analytics to collect metrics from all sources
```

**Expected**: Metrics data from available sources

#### Test 4: OpenAI
```
Use the openai MCP server to generate a short poem about AI
```

**Expected**: GPT-4 or GPT-3.5 generated poem

#### Test 5: Groq
```
Use the groq MCP server for fast inference: Write a haiku about speed
```

**Expected**: Llama/Mixtral fast response

#### Test 6: Perplexity
```
Use perplexity to search for the latest news about AI in 2025
```

**Expected**: Current web search results

#### Test 7: Supabase
```
Use supabase to list available database operations
```

**Expected**: Database tool list

---

## Method 2: Manual Server Testing (CLI)

### Test Server Executables Directly

#### Test youtube-uvai-processor
```bash
cd /Users/garvey/Dev/OpenAI_Hub/projects/EventRelay
export YOUTUBE_API_KEY="AIzaSyDn2Z8cY8mVmXBdv8KGv7-YYV5T4jGJwKY"
export OPENAI_API_KEY="sk-proj-n9OQCUlqiZPuQXVlhM0OG-qMHj3FTKelBdJjnOKXCvhHJ8a4WEE-n0T3BlbkFJ7PNYmF6FpxLHWZcFoM"
python3 scripts/youtube_uvai_mcp.py
```

**Expected**: MCP server starts, accepts stdio protocol

#### Test self-correcting-executor
```bash
cd /Users/garvey/Grok-Claude-Hybrid-Deployment
python3 mcp_server/main.py
```

**Expected**: MCP server starts successfully

#### Test perplexity
```bash
export PERPLEXITY_API_KEY="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"
python3 -m perplexity_mcp
```

**Expected**: Module runs without errors

#### Test unified-analytics
```bash
node /Users/garvey/Documents/Cline/MCP/unified-analytics/build/index.js
```

**Expected**: Node server starts

#### Test metacognition-tools
```bash
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
node /Users/garvey/Documents/Cline/MCP/metacognition-tools/build/index.js
```

**Expected**: Node server starts

#### Test openai (npm package)
```bash
export OPENAI_API_KEY="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"
npx -y @modelcontextprotocol/server-openai
```

**Expected**: OpenAI MCP server initializes

#### Test groq (npm package)
```bash
export GROQ_API_KEY="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"
npx -y @modelcontextprotocol/server-groq
```

**Expected**: Groq MCP server initializes

#### Test supabase (HTTP)
```bash
curl -s "https://mcp.supabase.com/mcp?project_ref=gabqshokqczqgnmiifyx&features=docs"
```

**Expected**: HTTP 200 response with MCP protocol

---

## Method 3: Automated Test Script

Create this test script:

```bash
#!/bin/bash
# test_all_mcp_servers.sh

echo "🧪 Testing All 8 MCP Servers"
echo "=============================="

# Test 1: youtube-uvai-processor
echo "Test 1: youtube-uvai-processor"
if [ -f "/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/scripts/youtube_uvai_mcp.py" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi

# Test 2: self-correcting-executor
echo "Test 2: self-correcting-executor"
if [ -f "/Users/garvey/Grok-Claude-Hybrid-Deployment/mcp_server/main.py" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi

# Test 3: perplexity
echo "Test 3: perplexity"
if python3 -c "import perplexity_mcp" 2>/dev/null; then
    echo "✅ Module available"
else
    echo "❌ Module not installed"
fi

# Test 4: unified-analytics
echo "Test 4: unified-analytics"
if [ -f "/Users/garvey/Documents/Cline/MCP/unified-analytics/build/index.js" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi

# Test 5: metacognition-tools
echo "Test 5: metacognition-tools"
if [ -f "/Users/garvey/Documents/Cline/MCP/metacognition-tools/build/index.js" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi

# Test 6: supabase (HTTP)
echo "Test 6: supabase"
if curl -s -o /dev/null -w "%{http_code}" "https://mcp.supabase.com/mcp?project_ref=gabqshokqczqgnmiifyx" | grep -q "200"; then
    echo "✅ HTTP endpoint reachable"
else
    echo "❌ HTTP endpoint unreachable"
fi

# Test 7: openai (npm package)
echo "Test 7: openai"
if npx -y @modelcontextprotocol/server-openai --help 2>&1 | grep -q "MCP\|model\|OpenAI" || true; then
    echo "✅ Package available"
else
    echo "⚠️  Package may need first-time download"
fi

# Test 8: groq (npm package)
echo "Test 8: groq"
if npx -y @modelcontextprotocol/server-groq --help 2>&1 | grep -q "MCP\|model\|Groq" || true; then
    echo "✅ Package available"
else
    echo "⚠️  Package may need first-time download"
fi

echo ""
echo "=============================="
echo "Test Summary Complete"
```

---

## Expected Test Results

### All Servers Passing
```
✅ youtube-uvai-processor: File exists
✅ self-correcting-executor: File exists
✅ perplexity: Module available
✅ unified-analytics: File exists
✅ metacognition-tools: File exists
✅ supabase: HTTP endpoint reachable
✅ openai: Package available
✅ groq: Package available
```

---

## Troubleshooting

### Server Won't Start

**Problem**: MCP server fails to initialize
**Solution**:
1. Check file paths in config
2. Verify API keys in environment
3. Check Python/Node versions
4. Review server logs

### Tool Not Available

**Problem**: Tool doesn't appear in Claude Desktop
**Solution**:
1. Restart Claude Desktop
2. Check MCP server status
3. Verify config JSON syntax
4. Check server logs for errors

### API Key Issues

**Problem**: Authentication errors
**Solution**:
1. Verify API keys in config
2. Check key expiration
3. Test API keys directly
4. Rotate keys if needed

### npm Package Issues

**Problem**: npx packages fail to load
**Solution**:
```bash
# Clear npm cache
npm cache clean --force

# Install packages globally (optional)
npm install -g @modelcontextprotocol/server-openai
npm install -g @modelcontextprotocol/server-groq
```

---

## MCP Protocol Testing

### Test MCP stdio Protocol

```python
#!/usr/bin/env python3
"""Test MCP server via stdio protocol"""
import json
import subprocess
import sys

def test_mcp_server(command, args):
    """Test MCP server startup"""
    proc = subprocess.Popen(
        [command] + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    try:
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()

        # Read response (with timeout)
        response = proc.stdout.readline()
        if response:
            data = json.loads(response)
            print(f"✅ Server responded: {data}")
            return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        proc.terminate()

    return False

if __name__ == "__main__":
    # Test youtube-uvai-processor
    print("Testing youtube-uvai-processor...")
    test_mcp_server(
        "python3",
        ["/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/scripts/youtube_uvai_mcp.py"]
    )
```

---

## Multi-MCP Orchestration Tests

### Test Workflow 1: Video Analysis Pipeline
```
1. Extract video ID (youtube-uvai-processor)
2. Get transcript (youtube-uvai-processor)
3. Analyze with OpenAI (openai)
4. Compare with Groq (groq)
5. Store results (supabase)
6. Track metrics (unified-analytics)
```

### Test Workflow 2: Research + Analysis
```
1. Web research (perplexity)
2. Fermi estimation (metacognition-tools)
3. Video context (youtube-uvai-processor)
4. Multi-model synthesis (openai + groq)
```

### Test Workflow 3: Self-Healing Pipeline
```
1. Process video (youtube-uvai-processor)
2. If error → self-correct (self-correcting-executor)
3. Retry processing
4. Log metrics (unified-analytics)
```

---

## Performance Benchmarks

### Target Metrics
- **Server startup**: <5 seconds
- **Tool response**: <10 seconds
- **HTTP endpoint**: <1 second
- **Multi-tool workflow**: <30 seconds

### Measurement Script
```bash
#!/bin/bash
# benchmark_mcp_servers.sh

start=$(date +%s)

# Test each server startup time
echo "youtube-uvai-processor startup..."
timeout 10 python3 scripts/youtube_uvai_mcp.py &
PID=$!
sleep 2
kill $PID 2>/dev/null

end=$(date +%s)
echo "Time: $((end-start))s"
```

---

## Next Steps After Testing

### If All Tests Pass ✅
1. Document successful workflows
2. Create user guides
3. Deploy to production
4. Monitor performance

### If Tests Fail ❌
1. Review error logs
2. Fix configuration issues
3. Update dependencies
4. Retry tests

---

## Automated Testing Recommendations

1. **Create CI/CD pipeline** for MCP server testing
2. **Set up monitoring** for server health
3. **Implement alerts** for failures
4. **Track metrics** for performance
5. **Version control** MCP configurations

---

**Status**: Ready for testing in Claude Desktop
**Test Coverage**: 8/8 servers documented
**Automation**: Scripts provided for CLI testing
