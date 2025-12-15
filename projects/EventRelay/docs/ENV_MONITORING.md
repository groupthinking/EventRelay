# Environment Configuration Monitoring

## Overview

EventRelay provides a comprehensive environment configuration management system that makes it easy to set up, validate, and monitor API keys as the project grows. The system includes:

1. **Interactive Setup** - Guided CLI to create and populate `.env` file
2. **Automatic Validation** - Validates API key format and required configurations
3. **Real-time Monitoring** - Watches `.env` for changes and validates automatically
4. **MCP Integration Strategy** - Leverages existing MCP tools for advanced workflows

## Quick Start

### 1. Initial Setup

```bash
# Interactive setup (recommended for first-time users)
python3 scripts/setup_env.py

# Manual setup
cp .env.example .env
# Edit .env and add your API keys
```

### 2. Validate Configuration

```bash
# One-time validation
python3 scripts/validate_env.py
```

### 3. Monitor for Changes (Development)

```bash
# Start monitoring (watches .env file for changes)
python3 scripts/monitor_env.py
```

## Available Tools

### `scripts/setup_env.py` - Interactive Setup

Provides a guided CLI experience to create and populate your `.env` file.

**Features:**
- ✅ Checks for existing `.env` file
- ✅ Copies from `.env.example` if needed
- ✅ Interactive prompts with help URLs for each API key
- ✅ Shows where to obtain each key
- ✅ Preserves existing values
- ✅ Validates that at least one AI provider key is set

**Usage:**
```bash
python3 scripts/setup_env.py
```

**Example Session:**
```
🔑 EventRelay Environment Setup
============================================================

No .env file found. Creating from template...
✓ Created .env from template

📝 API Key Configuration
============================================================

Google Gemini API
Description: PRIMARY key for AI analysis and code generation
Required: Yes
Get your key from: https://aistudio.google.com/app/apikey
Enter GEMINI_API_KEY (or press Enter to skip): AIza...
✓ Set GEMINI_API_KEY

✅ Setup Complete
============================================================
✓ Your .env file is ready!
```

### `scripts/validate_env.py` - Configuration Validator

Validates your `.env` file configuration and checks for common issues.

**Features:**
- ✅ Checks for required API keys
- ✅ Validates API key format with regex patterns
- ✅ Detects placeholder values that need replacement
- ✅ Provides actionable error messages with help URLs
- ✅ Color-coded output (errors, warnings, info)

**Usage:**
```bash
python3 scripts/validate_env.py
```

**Example Output:**
```
🔍 Environment Validation Results
============================================================

✅ Environment validation passed!

Configured API keys:
  ✓ GEMINI_API_KEY: ****
  ✓ YOUTUBE_API_KEY: ****

You're ready to run the application!
```

### `scripts/monitor_env.py` - Real-time Monitor

Watches your `.env` file for changes and automatically validates on each update.

**Features:**
- ✅ Real-time file watching (uses `watchdog` if available)
- ✅ Automatic validation on file change
- ✅ Fallback to polling if `watchdog` not installed
- ✅ Timestamps for each change detection
- ✅ Immediate feedback on configuration issues

**Usage:**
```bash
# Install watchdog for efficient monitoring (optional)
pip install watchdog

# Start monitoring
python3 scripts/monitor_env.py
```

**Example Output:**
```
🔍 Environment Configuration Monitor
============================================================

Running initial validation...
✅ Environment validation passed!

Starting file monitor...
✓ Started monitoring /path/to/EventRelay/.env
Press Ctrl+C to stop

[2024-12-02 10:30:45] .env file changed. Validating...
✅ Configuration is valid
```

## API Key Requirements

### Required Keys (At Least ONE)

You must have at least ONE of the following AI provider keys:

| Key | Provider | Get Key From | Purpose |
|-----|----------|--------------|---------|
| `GEMINI_API_KEY` | Google Gemini | [AI Studio](https://aistudio.google.com/app/apikey) | **PRIMARY** - AI analysis and code generation |
| `OPENAI_API_KEY` | OpenAI | [Platform](https://platform.openai.com/api-keys) | Alternative AI provider |

### Optional Keys (Recommended)

| Key | Provider | Get Key From | Purpose |
|-----|----------|--------------|---------|
| `YOUTUBE_API_KEY` | YouTube Data API v3 | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) | Enhanced video metadata |
| `ANTHROPIC_API_KEY` | Anthropic Claude | [Console](https://console.anthropic.com/settings/keys) | Additional AI provider |
| `ASSEMBLYAI_API_KEY` | AssemblyAI | [Dashboard](https://www.assemblyai.com/app/account) | Alternative transcription |

## API Key Format Validation

The validator checks API key formats to catch common errors:

```python
KEY_PATTERNS = {
    'GEMINI_API_KEY': r'^[A-Za-z0-9_-]{30,}$',
    'OPENAI_API_KEY': r'^sk-[A-Za-z0-9]{20,}$',
    'ANTHROPIC_API_KEY': r'^sk-ant-[A-Za-z0-9_-]{20,}$',
    'YOUTUBE_API_KEY': r'^AIza[A-Za-z0-9_-]{35}$',
    'ASSEMBLYAI_API_KEY': r'^[a-f0-9]{32}$',
}
```

## MCP Integration Strategy

EventRelay follows an **MCP-First Design** philosophy. When available, MCP tools should be used for environment management.

### Available MCP Tools

The project includes several MCP servers that can be leveraged:

1. **YouTube MCP Server** (`mcp_youtube-0.2.0/mcp_youtube.py`)
   - Already uses `YOUTUBE_API_KEY` from environment
   
2. **Video Analysis MCP Server** (`external/mcp_servers/video_analysis_mcp_server.py`)
   - Uses `GEMINI_API_KEY` from environment

3. **YouTube Extension MCP Server** (`external/mcp_servers/youtube_extension_mcp_server.py`)
   - Connects to backend API

### MCP Environment Best Practices

When working with MCP servers:

1. **Always check MCP configuration first** in `.github/mcp-servers.json`
2. **Environment variables are passed via `env` block** in MCP server config
3. **No need to manually validate** - MCP servers will fail gracefully if keys are missing
4. **Use the monitoring script** during development to catch issues early

Example MCP server configuration:
```json
{
  "mcpServers": {
    "youtube": {
      "command": "python",
      "args": ["${workspaceFolder}/mcp_youtube-0.2.0/mcp_youtube.py"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}",
        "YOUTUBE_API_KEY": "${env:YOUTUBE_API_KEY}"
      }
    }
  }
}
```

### When to Use Which Tool

| Scenario | Recommended Tool |
|----------|------------------|
| First-time setup | `scripts/setup_env.py` |
| CI/CD validation | `scripts/validate_env.py` |
| Development workflow | `scripts/monitor_env.py` |
| MCP server integration | Use MCP server directly (auto-validates) |
| Adding new API keys | Update `.env.example` + `setup_env.py` + `validate_env.py` |

## Adding New API Keys

As EventRelay grows and adds more integrations, follow this process:

### 1. Update `.env.example`

Add the new key with:
- Clear comment explaining the purpose
- Link to where to get the key
- Placeholder value

```bash
# New Service API Key - Get from: https://service.com/api-keys
# Optional: Used for XYZ feature
NEW_SERVICE_API_KEY=your-new-service-key
```

### 2. Update `scripts/setup_env.py`

Add to the `API_KEYS` dictionary:

```python
API_KEYS = {
    # ... existing keys ...
    'NEW_SERVICE_API_KEY': {
        'name': 'New Service API',
        'url': 'https://service.com/api-keys',
        'required': False,  # or True
        'priority': 7,  # adjust as needed
        'description': 'Used for XYZ feature'
    }
}
```

### 3. Update `scripts/validate_env.py`

Add validation pattern if needed:

```python
KEY_PATTERNS = {
    # ... existing patterns ...
    'NEW_SERVICE_API_KEY': r'^ns-[A-Za-z0-9]{32}$',  # example pattern
}
```

### 4. Update MCP Configuration (if applicable)

If the key is used by an MCP server, add it to `.github/mcp-servers.json`:

```json
{
  "mcpServers": {
    "new-service": {
      "command": "python",
      "args": ["${workspaceFolder}/path/to/mcp_server.py"],
      "env": {
        "NEW_SERVICE_API_KEY": "${env:NEW_SERVICE_API_KEY}"
      }
    }
  }
}
```

## Automated Monitoring Strategy

For production environments, consider:

### Option 1: CI/CD Integration

Add validation to your CI pipeline:

```yaml
# .github/workflows/validate-env.yml
name: Validate Environment
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Validate .env.example
        run: python3 scripts/validate_env.py
```

### Option 2: Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
python3 scripts/validate_env.py
if [ $? -ne 0 ]; then
    echo "❌ Environment validation failed"
    exit 1
fi
```

### Option 3: Development Container

Include monitoring in your dev container startup:

```json
// .devcontainer/devcontainer.json
{
  "postStartCommand": "python3 scripts/monitor_env.py &"
}
```

## Troubleshooting

### Issue: "No valid AI provider key found"

**Solution:** You need at least ONE of:
- `GEMINI_API_KEY` (recommended)
- `OPENAI_API_KEY`

Run `python3 scripts/setup_env.py` to set up interactively.

### Issue: "API key format looks incorrect"

**Solution:** Check that your API key matches the expected format. Common issues:
- Copied extra spaces or newlines
- Missing key prefix (e.g., `sk-` for OpenAI)
- Incomplete key

### Issue: "watchdog not installed" warning

**Solution:** Install watchdog for better performance:
```bash
pip install watchdog
```

The monitor will still work without it using polling mode.

### Issue: Changes not detected by monitor

**Solution:**
1. Make sure you're editing the correct `.env` file
2. Save the file properly (some editors use atomic writes)
3. Check file permissions
4. Try polling mode if watchdog isn't working

## Security Best Practices

1. **Never commit `.env` files** - Already in `.gitignore`
2. **Use different keys for dev/prod** - Maintain separate `.env.production`
3. **Rotate keys periodically** - Especially if exposed
4. **Use environment-specific templates** - `.env.example`, `.env.production.example`
5. **Validate in CI/CD** - Catch issues before deployment
6. **Monitor for placeholder values** - The validator catches these automatically

## Integration with Agent Self-Creation System

EventRelay has an agent gap detection system (`scripts/manage_custom_agents.py`) that can identify when new custom GitHub Copilot agents are needed. The environment monitoring system complements this by:

1. **Detecting new API key requirements** - When new services are integrated
2. **Validating agent dependencies** - Ensuring agents have required credentials
3. **Alerting on missing keys** - Before agents attempt to use them

For more on the agent system, see:
- `docs/AGENT_SELF_CREATION.md`
- `AGENT_SELF_CREATION_SUMMARY.md`
- `scripts/manage_custom_agents.py`

## Summary

EventRelay's environment management system provides:

✅ **Easy Setup** - Interactive CLI for first-time users
✅ **Automatic Validation** - Catches issues before runtime
✅ **Real-time Monitoring** - Continuous feedback during development
✅ **MCP-First Design** - Leverages existing MCP infrastructure
✅ **Extensible** - Easy to add new API keys and integrations
✅ **Secure** - Best practices enforced by default

Start with `python3 scripts/setup_env.py` and you'll be up and running in minutes!
