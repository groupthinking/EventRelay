# GitHub Configuration for EventRelay

This directory contains GitHub-specific configuration files that enhance the development experience with AI coding assistants like GitHub Copilot.

## Files

### `copilot-instructions.md`
Custom instructions for GitHub Copilot that provide context about the EventRelay project, including:
- Architecture overview and design patterns
- Code quality standards and best practices
- Technology stack details
- Common development tasks and workflows
- Security guidelines
- Testing standards
- References to evaluated resources and optional tools

**Purpose**: Helps Copilot generate more accurate and contextually appropriate code suggestions.

### `RESOURCE_EVALUATION.md`
Comprehensive evaluation of recommended resources for EventRelay integration:
- [langwatch/better-agents](https://github.com/langwatch/better-agents) - Agent testing and reliability toolkit
- [github/github-mcp-server](https://github.com/github/github-mcp-server) - Official GitHub MCP integration
- [Google Cloud agent-starter-pack](https://googlecloudplatform.github.io/agent-starter-pack/) - Production agent templates

Each resource is evaluated for relevance, value add, integration effort, and includes a decision (integrate, defer, or skip) with rationale.

**Purpose**: Documents evaluation decisions and provides guidance on future enhancements.

### `mcp-config.md`
Documentation for Model Context Protocol (MCP) server configuration, including:
- Available MCP servers and their capabilities
- Configuration examples for different editors
- Environment variable setup
- Troubleshooting guide
- Best practices for MCP usage

**Purpose**: Guides developers in setting up and using MCP servers for enhanced AI capabilities.

### `mcp-servers.json`
Ready-to-use MCP server configuration file that can be:
- Used directly by compatible editors (VS Code, Cursor)
- Copied to editor-specific configuration locations
- Modified for custom MCP server setups

**Purpose**: Provides a working MCP configuration that integrates with EventRelay's agent framework.

## Usage

### For GitHub Copilot Users

GitHub Copilot automatically reads `copilot-instructions.md` to understand project context. No additional setup is needed beyond having Copilot enabled in your editor.

To get the most value:
1. Ensure you're working in the repository root
2. Ask Copilot questions about project-specific patterns
3. Reference project concepts in comments to get contextual suggestions

### For MCP Server Users

#### VS Code / Cursor
1. Copy `mcp-servers.json` to your editor's MCP configuration location:
   - Cursor: `~/.cursor/mcp.json`
   - VS Code: Workspace settings or user settings

2. Update paths if your workspace location differs

3. Set required environment variables in `.env`:
   ```bash
   YOUTUBE_API_KEY=your_key
   MCP_TIMEOUT=300
   MCP_MAX_CONCURRENT=5
   ```

4. Restart your editor to activate MCP servers

#### Programmatic Usage
See `mcp-config.md` for examples of using MCP servers from Python code.

## Development Environment Setup

The repository also includes:
- `../.devcontainer/` - Dev container configuration for consistent environments
- `../.vscode/` - VS Code workspace settings and recommended extensions

## Updating Instructions

When project patterns or architecture change:
1. Update `copilot-instructions.md` to reflect new patterns
2. Update `mcp-config.md` if MCP server capabilities change
3. Validate changes with validation script: `python3 scripts/validate_copilot_instructions.py`
4. Test that instructions produce better AI suggestions
5. Commit changes to keep AI context current

## Related Files

- `../docs/CLAUDE.md` - Claude AI master framework
- `../.claude/claude_instructions.md` - Claude code-specific instructions
- `../.cursor/rules/` - Cursor editor-specific rules
- `../README.md` - Project overview and setup

## Validation

To validate that the Copilot instructions meet all requirements:

```bash
# Run validation script
python3 scripts/validate_copilot_instructions.py
```

The script checks for:
- Required sections (Environment Variables, Database Connections, etc.)
- Backend-frontend compatibility documentation
- API key management guidance
- Code examples in Python, TypeScript, and Bash
- Database configuration documentation

## Contributing

When adding new features or patterns:
1. Document them in relevant instruction files
2. Add examples to help AI assistants understand usage
3. Keep instructions focused on patterns, not implementation details
4. Run validation script to ensure completeness
5. Test that AI tools produce better suggestions with updated context
