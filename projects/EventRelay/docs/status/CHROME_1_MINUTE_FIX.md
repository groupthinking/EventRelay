# ⚠️ URGENT: Chrome Closing After 1 Minute

## Critical Issue
Chrome is now closing after just **1 minute** instead of 5 minutes. This indicates the problem is escalating.

## Immediate Actions

### 1. Kill ALL Automation Processes
```bash
# Kill everything that might interfere
pkill -f "mcp"
pkill -f "MCP"
pkill -f "playwright"
pkill -f "netlify"
pkill -f "llama"
pkill -f "selenium"
pkill -f "puppeteer"
pkill -f "automation"
```

### 2. Temporarily Disable ALL MCP Servers in Cursor
```bash
# Backup current config
cp ~/.cursor/mcp.json ~/.cursor/mcp.json.backup.emergency

# Disable all MCP servers
echo '{"mcpServers": {}}' > ~/.cursor/mcp.json

# Restart Cursor
pkill -f "Cursor" && sleep 3 && open -a Cursor
```

### 3. Test Chrome with Clean Profile
```bash
chmod +x test_chrome_clean.sh
./test_chrome_clean.sh
```

## Possible Causes

### 1. MCP Server Interference
The llama and Netlify MCP servers are running and might be sending signals to close Chrome.

### 2. Browser Automation Detection
Chrome might be detecting automation tools and self-terminating as a security measure.

### 3. System Resource Protection
MacOS might be killing Chrome if it detects unusual automation activity.

### 4. Cursor Extension Conflict
A Cursor extension might be interfering with Chrome.

## Diagnostic Steps

### Step 1: Check What's Running
```bash
# See all potentially interfering processes
ps aux | grep -E "chrome|Chrome|mcp|MCP|playwright|selenium|puppeteer" | grep -v grep
```

### Step 2: Check Chrome Launch
```bash
# Launch Chrome with verbose logging
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --enable-logging \
    --v=1 \
    --dump-browser-histograms \
    2>&1 | tee chrome_verbose.log
```

### Step 3: Monitor System Activity
```bash
# Watch for what kills Chrome
sudo fs_usage | grep -i chrome
```

## Nuclear Option - Complete Reset

If nothing else works:

### 1. Completely Remove Cursor MCP
```bash
# Remove all MCP configurations
rm ~/.cursor/mcp.json
rm -rf ~/.cursor/mcp/
```

### 2. Reset Chrome
```bash
# Reset Chrome to factory settings
rm -rf ~/Library/Application\ Support/Google/Chrome/
rm ~/Library/Preferences/com.google.Chrome.plist
```

### 3. Restart Mac
```bash
sudo shutdown -r now
```

## Alternative Browsers

While we fix this issue, use:
- **Safari**: Won't be affected by automation tools
- **Firefox**: Download from https://www.mozilla.org/firefox/
- **Brave**: Download from https://brave.com/

## Test Script

Run this to test if Chrome stays open:
```bash
./test_chrome_clean.sh
```

This script:
1. Kills all MCP processes
2. Creates a clean Chrome profile
3. Launches Chrome with debugging
4. Monitors for 10 minutes
5. Shows what killed it if it closes

## Emergency Workaround

Use Chrome in a Docker container:
```bash
docker run -d \
  --name chrome \
  -p 9222:9222 \
  zenika/alpine-chrome \
  --no-sandbox \
  --remote-debugging-address=0.0.0.0 \
  --remote-debugging-port=9222
```

Then access at: http://localhost:9222

## Root Cause Investigation

The fact that Chrome now closes after 1 minute (not 5) suggests:
1. Something changed when we modified MCP configuration
2. MCP servers are actively interfering
3. There's a cascading timeout issue

## Contact Support

If this persists:
1. Contact Cursor support about MCP interference
2. Check Chrome enterprise policies: chrome://policy
3. Review Mac security settings: System Preferences > Security & Privacy
