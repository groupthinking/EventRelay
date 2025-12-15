# Copilot Setup Guide for EventRelay

This guide walks you through setting up GitHub Copilot with enhanced capabilities for the EventRelay project.

## Prerequisites

1. **GitHub Copilot Subscription**: You need an active Copilot subscription
2. **Supported Editor**: VS Code, Cursor, or another Copilot-compatible editor
3. **Python 3.9+**: For running MCP servers
4. **Node.js 18+**: For frontend development

## Quick Start

### 1. Clone and Setup Repository

```bash
git clone https://github.com/groupthinking/EventRelay.git
cd EventRelay

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .[dev,youtube,ml]

# Install frontend dependencies
npm install --prefix frontend
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys (Required)
YOUTUBE_API_KEY=your_youtube_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional

# MCP Configuration
MCP_TIMEOUT=300
MCP_MAX_CONCURRENT=5
MCP_RETRY_ATTEMPTS=3
MCP_BATCH_SIZE=3
MCP_ENABLE_CIRCUIT_BREAKER=true

# Google Cloud (for Speech-to-Text)
GOOGLE_SPEECH_PROJECT_ID=your_project_id
GOOGLE_SPEECH_LOCATION=us-central1
GOOGLE_SPEECH_RECOGNIZER=transcript-recognizer
GOOGLE_SPEECH_GCS_BUCKET=your_gcs_bucket
```

Get API keys from:
- **YouTube Data API**: https://console.cloud.google.com/apis/credentials
- **Gemini API**: https://makersuite.google.com/app/apikey
- **OpenAI API**: https://platform.openai.com/api-keys

### 3. VS Code Setup

#### Install Recommended Extensions

Open the project in VS Code and install recommended extensions when prompted, or manually install:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.black-formatter
code --install-extension charliermarsh.ruff
code --install-extension dbaeumer.vscode-eslint
code --install-extension esbenp.prettier-vscode
code --install-extension GitHub.copilot
code --install-extension GitHub.copilot-chat
```

#### Open Workspace

Open the workspace file for best experience:
```bash
code .vscode/eventrelay.code-workspace
```

### 4. Configure MCP Servers (Optional but Recommended)

MCP servers provide enhanced AI capabilities for video processing and analysis.

#### Option A: VS Code Settings

Add to your VS Code `settings.json`:

```json
{
  "mcp.servers": {
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

#### Option B: Cursor Editor

If using Cursor, copy `.github/mcp-servers.json` to `~/.cursor/mcp.json`:

```bash
cp .github/mcp-servers.json ~/.cursor/mcp.json
```

Edit paths in the file to match your system.

## Using Copilot with EventRelay

### Custom Instructions

Copilot automatically reads `.github/copilot-instructions.md` which provides:
- Project architecture overview
- Code quality standards
- Testing guidelines
- Security best practices
- Common patterns and anti-patterns

### Smart Code Suggestions

Copilot will now provide context-aware suggestions:

**Example 1: Adding an API Endpoint**
```python
# Type a comment describing what you want:
# Create an API endpoint to process a YouTube video
# Copilot will suggest code following project patterns
```

**Example 2: Frontend Integration**
```typescript
// Type: Create a hook to fetch video analysis
// Copilot will suggest code using project's API service patterns
```

### Copilot Chat Tips

Ask questions using project context:

```
Q: How do I add a new MCP agent?
Q: What's the test video ID I should use?
Q: Show me how to process a video with the unified processor
Q: What's the correct error handling pattern for this project?
```

## Verifying Setup

### 1. Check Copilot Status

In VS Code:
- Open Command Palette (Cmd/Ctrl + Shift + P)
- Type "Copilot: Status"
- Should show "Ready" or "Signed in"

### 2. Test Copilot Suggestions

Create a new file and type:
```python
def process_youtube_video(
```

Copilot should suggest parameters and implementation based on project context.

### 3. Test MCP Servers (if configured)

```bash
# Test YouTube MCP server
python mcp_youtube-0.2.0/mcp_youtube.py --help

# Test backend is running
python -c "import uvai.api.main; print('Backend imports OK')"
```

### 4. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_video_processor.py -v
```

## Common Issues and Solutions

### Issue: Copilot Not Providing Suggestions

**Solution 1**: Check Copilot status
```
Cmd/Ctrl + Shift + P → "Copilot: Diagnose"
```

**Solution 2**: Reload VS Code
```
Cmd/Ctrl + Shift + P → "Developer: Reload Window"
```

**Solution 3**: Check for errors in Output
```
View → Output → Select "GitHub Copilot"
```

### Issue: MCP Servers Not Starting

**Solution 1**: Check Python environment
```bash
which python  # Should point to .venv/bin/python
python --version  # Should be 3.9+
```

**Solution 2**: Install MCP dependencies
```bash
pip install mcp fastmcp
```

**Solution 3**: Check environment variables
```bash
echo $YOUTUBE_API_KEY  # Should not be empty
```

### Issue: Import Errors

**Solution**: Ensure PYTHONPATH is set
```bash
export PYTHONPATH=$(pwd)
```

Add to your shell profile (~/.bashrc, ~/.zshrc):
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/EventRelay"
```

## Advanced Configuration

### Custom Copilot Instructions

Create `.copilot/instructions.md` in your home directory for global instructions:

```markdown
# My Global Copilot Instructions

- Always write comprehensive docstrings
- Prefer functional programming patterns
- Use type hints for all Python functions
```

### Project-Specific Snippets

Add to `.vscode/eventrelay.code-workspace`:

```json
{
  "settings": {
    "editor.snippetSuggestions": "top"
  }
}
```

### MCP Server Development

To create a custom MCP server:

1. Copy template: `external/mcp_servers/youtube_extension_mcp_server.py`
2. Implement tools following MCP protocol
3. Register in `.github/mcp-servers.json`
4. Test with: `python your_mcp_server.py`

## Best Practices

### 1. Keep Instructions Updated

When you add new patterns or conventions, update:
- `.github/copilot-instructions.md`
- `.claude/claude_instructions.md`
- `docs/CLAUDE.md`

### 2. Use Descriptive Comments

Instead of:
```python
# process video
```

Use:
```python
# Process YouTube video using unified processor with error handling and caching
```

### 3. Review Suggestions

Always review Copilot suggestions for:
- Security issues (hardcoded secrets, SQL injection)
- Project conventions (test video IDs, file organization)
- Error handling completeness
- Type safety

### 4. Provide Context

When working in a new file, add context at the top:
```python
"""
Video Analysis Service

This module provides video analysis capabilities using Gemini API.
Follows EventRelay patterns for error handling and logging.
"""
```

## Resources

- **Project README**: `README.md`
- **Architecture Guide**: `docs/CLAUDE.md`
- **API Documentation**: http://localhost:8000/docs (when backend running)
- **MCP Documentation**: `.github/mcp-config.md`
- **Test Standards**: `.claude/claude_instructions.md`

## Getting Help

1. **Ask Copilot Chat**: It has access to project instructions
2. **Check Documentation**: See `docs/` directory
3. **Run Tests**: Tests demonstrate correct patterns
4. **Review Examples**: See `examples/` directory

## Next Steps

1. ✅ Complete setup steps above
2. 📖 Read `docs/CLAUDE.md` for architecture overview
3. 🧪 Run tests to understand project patterns
4. 🚀 Start coding with Copilot assistance
5. 📝 Update instructions as you learn new patterns

---

**Questions or Issues?**

Open an issue on GitHub or check the project documentation.

**Happy Coding with Copilot!** 🚀
