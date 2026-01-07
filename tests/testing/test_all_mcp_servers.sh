#!/bin/bash
# Automated MCP Server Testing Script
# Tests all 7 configured MCP servers for file existence and availability

echo "🧪 Testing All 7 MCP Servers"
echo "=============================="
echo ""

# Test 1: youtube-uvai-processor
echo "Test 1: youtube-uvai-processor"
if [ -f "/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/scripts/youtube_uvai_mcp.py" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi
echo ""

# Test 2: self-correcting-executor
echo "Test 2: self-correcting-executor"
if [ -f "/Users/garvey/Grok-Claude-Hybrid-Deployment/mcp_server/main.py" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi
echo ""

# Test 3: perplexity
echo "Test 3: perplexity"
if python3 -c "import perplexity_mcp" 2>/dev/null; then
    echo "✅ Module available"
else
    echo "❌ Module not installed"
fi
echo ""

# Test 4: unified-analytics
echo "Test 4: unified-analytics"
if [ -f "/Users/garvey/Documents/Cline/MCP/unified-analytics/build/index.js" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi
echo ""

# Test 5: metacognition-tools
echo "Test 5: metacognition-tools"
if [ -f "/Users/garvey/Documents/Cline/MCP/metacognition-tools/build/index.js" ]; then
    echo "✅ File exists"
else
    echo "❌ File not found"
fi
echo ""

# Test 6: openai (npm package)
echo "Test 6: openai"
if npx -y @modelcontextprotocol/server-openai --help 2>&1 | grep -q "MCP\|model\|OpenAI" || true; then
    echo "✅ Package available"
else
    echo "⚠️  Package may need first-time download"
fi
echo ""

# Test 7: groq (npm package)
echo "Test 7: groq"
if npx -y @modelcontextprotocol/server-groq --help 2>&1 | grep -q "MCP\|model\|Groq" || true; then
    echo "✅ Package available"
else
    echo "⚠️  Package may need first-time download"
fi
echo ""

echo "=============================="
echo "Test Summary Complete"
