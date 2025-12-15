# Chrome Browser 5-Minute Timeout Fix

## Problem Identified
Chrome browser closes after exactly 5 minutes when running alongside Playwright/MCP automation tools due to multiple hardcoded 300-second (5-minute) timeout settings throughout the system.

## Root Causes Found

### 1. System-Wide 5-Minute Timeouts
Multiple components have 300-second timeout settings:
- **llama_agent_config.json**: `"timeout": 300` 
- **enterprise_mcp_server.py**: `max_timeout_seconds: int = 300`
- **error_handling_middleware.py**: `timeout_seconds: float = 300.0`
- **Various services**: cache_ttl, cooldown periods, health check intervals all set to 300 seconds

### 2. MCP Playwright Server Configuration
- Running via: `npx @playwright/mcp@latest`
- No explicit browser timeout configuration in `/Users/garvey/.cursor/mcp.json`
- Likely using default timeout that kills browser instances after 5 minutes

### 3. Browser Instance Conflict
The Playwright MCP server is likely:
- Managing Chrome instances with automation protocols
- Applying the 5-minute timeout to ALL Chrome instances (including your regular browser)
- Not distinguishing between automated test browsers and your personal Chrome browser

## Solutions

### Option 1: Increase Timeout Settings (Quick Fix)
Modify the timeout settings to a much longer duration (e.g., 2 hours = 7200 seconds):

```json
// config/llama_agent_config.json
{
  "llama_agent": {
    "processing": {
      "timeout": 7200  // Changed from 300
    }
  }
}
```

```python
# scripts/enterprise_mcp_server.py
class CircuitBreakerConfig:
    max_timeout_seconds: int = 7200  # Changed from 300
```

```python
# src/youtube_extension/backend/middleware/error_handling_middleware.py
timeout_seconds: float = 7200.0  # Changed from 300.0
```

### Option 2: Disable MCP Playwright When Not Needed (Recommended)
Stop the Playwright MCP server when you're not actively using it for automation:

```bash
# Kill the Playwright MCP server processes
pkill -f "mcp-server-playwright"
pkill -f "@playwright/mcp"
```

### Option 3: Configure Playwright to Ignore Personal Chrome
Create a custom Playwright configuration that:
1. Uses a separate browser profile for automation
2. Doesn't interfere with your personal Chrome instance
3. Only controls browsers it explicitly launches

Create `playwright-mcp-config.json`:
```json
{
  "browserOptions": {
    "headless": false,
    "timeout": 0,  // No timeout
    "ignoreDefaultArgs": ["--enable-automation"],
    "args": [
      "--user-data-dir=/tmp/playwright-chrome",  // Separate profile
      "--no-sandbox",
      "--disable-blink-features=AutomationControlled"
    ]
  }
}
```

### Option 4: Use Different Browsers
- Use Chrome for personal browsing
- Configure Playwright to use Firefox or WebKit for automation
- This prevents any conflict between automation and personal use

## Immediate Actions

### 1. Stop Current Playwright Processes
```bash
# Stop the MCP Playwright server
pkill -f "mcp-server-playwright"
pkill -f "@playwright/mcp"
```

### 2. Modify MCP Configuration (Optional)
If you need Playwright MCP, configure it with no timeout:

Update `/Users/garvey/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "Playwright": {
      "command": "npx",
      "args": [
        "@playwright/mcp@latest",
        "--timeout=0"  // Add this to disable timeout
      ],
      "env": {
        "PLAYWRIGHT_BROWSER_TIMEOUT": "0",
        "PLAYWRIGHT_DEFAULT_TIMEOUT": "0"
      }
    }
  }
}
```

### 3. Create Browser Isolation Script
Save as `start_isolated_chrome.sh`:
```bash
#!/bin/bash
# Start Chrome with a profile that won't be affected by Playwright
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --user-data-dir="$HOME/ChromePersonal" \
  --disable-blink-features=AutomationControlled \
  --excludeSwitches=enable-automation \
  --disable-infobars
```

## Testing the Fix

1. **Kill current Playwright processes**:
   ```bash
   pkill -f playwright
   pkill -f mcp-server
   ```

2. **Start Chrome normally** and verify it stays open past 5 minutes

3. **If you need Playwright**, restart it with the new configuration

4. **Monitor for stability** using:
   ```bash
   # Check if Chrome is still running after 6 minutes
   sleep 360 && ps aux | grep -i chrome
   ```

## Long-term Solution

Consider implementing a more robust browser management strategy:

1. **Separate Automation Environment**: Run all automation tools in Docker containers
2. **Profile Isolation**: Use distinct browser profiles for automation vs personal use
3. **Conditional MCP Loading**: Only load Playwright MCP when actively developing/testing
4. **Resource Management**: Implement proper cleanup and resource limits for automation tools

## Verification

After implementing the fix, verify:
- [ ] Chrome stays open for more than 5 minutes
- [ ] Playwright automation still works when needed
- [ ] No performance degradation
- [ ] System resources are not being exhausted

## Additional Notes

The 5-minute timeout appears to be a safety mechanism to prevent runaway browser processes from consuming system resources. However, it's incorrectly affecting your personal Chrome usage. The solutions above will isolate automation from personal browsing while maintaining the safety benefits for actual automation tasks.
