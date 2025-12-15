# GitHub Copilot Custom Agents for EventRelay

This directory contains custom agent configurations for GitHub Copilot. These agents are specialized AI assistants that provide expert guidance for different aspects of the EventRelay project.

## What are Custom Agents?

GitHub Copilot custom agents are specialized AI assistants defined in `.agent.md` files. Each agent has:
- **Specific expertise** in a domain or technology
- **Contextual knowledge** about the EventRelay project
- **Best practices** and patterns specific to this codebase
- **Boundaries** defining what they can and cannot modify

## Available Agents

### 1. Python Backend Agent (`python-backend.agent.md`)
**Expertise:** FastAPI, async services, SQLAlchemy, backend architecture

Use when:
- Creating or modifying API endpoints
- Working with database models and migrations
- Implementing async services
- Adding backend business logic

**Key Features:**
- Type hints and type safety guidance
- FastAPI best practices
- Async/await patterns
- Error handling standards
- Database operations with SQLAlchemy

### 2. Frontend Agent (`frontend.agent.md`)
**Expertise:** React 18+, TypeScript, hooks, component architecture

Use when:
- Building React components
- Creating custom hooks
- Integrating with backend APIs
- Writing frontend tests with Jest/RTL

**Key Features:**
- TypeScript strict mode patterns
- React hooks best practices
- API integration patterns
- Component testing strategies
- Performance optimization techniques

### 3. Testing Agent (`testing.agent.md`)
**Expertise:** pytest, Jest, test coverage, quality assurance

Use when:
- Writing unit or integration tests
- Improving test coverage
- Debugging test failures
- Setting up test fixtures

**Key Features:**
- Test patterns for async code
- Fixture organization
- Mocking strategies
- Coverage analysis
- Standard test video ID usage

### 4. MCP Agent (`mcp.agent.md`)
**Expertise:** Model Context Protocol, agent orchestration, JSON-RPC

Use when:
- Implementing MCP tools
- Creating agent workflows
- Building A2A (Agent-to-Agent) communication
- Integrating MCP servers

**Key Features:**
- JSON-RPC 2.0 protocol
- MCP tool definitions
- Agent orchestration patterns
- Circuit breaker implementation
- Context isolation

### 5. Documentation Agent (`documentation.agent.md`)
**Expertise:** Technical writing, Markdown, API documentation

Use when:
- Writing or updating documentation
- Creating tutorials or guides
- Documenting API endpoints
- Maintaining README files

**Key Features:**
- Markdown formatting standards
- Documentation structure patterns
- Code example best practices
- API documentation templates
- Changelog management

### 6. Video Processing Agent (`video-processing.agent.md`)
**Expertise:** Video processing, transcription, AI analysis, event extraction

Use when:
- Processing YouTube videos
- Extracting transcripts
- Implementing event extraction
- Integrating AI providers (Gemini, OpenAI)

**Key Features:**
- Unified video processor patterns
- Transcription fallback strategies
- AI integration for event extraction
- RAG (Retrieval-Augmented Generation) grounding
- Caching strategies

## How to Use Custom Agents

### In GitHub Copilot Chat

When using GitHub Copilot Chat, you can invoke specific agents:

```
@python-backend How do I create a new API endpoint?
@frontend Create a hook to fetch video data
@testing Write tests for the video processor
@mcp Show me how to implement an MCP tool
@documentation Document this API endpoint
@video-processing How do I extract events from a transcript?
```

### Automatic Agent Selection

GitHub Copilot automatically selects the most appropriate agent based on:
- The file you're editing (`.py` → python-backend, `.tsx` → frontend)
- Your question context
- The task you're performing

### Agent Priority

Agents are discovered in this order:
1. **Repository-specific**: `.github/agents/` (this directory) - highest priority
2. **Organization-wide**: `{org}/.github/agents/`
3. **User-specific**: `~/.copilot/agents/`

## Agent Naming Convention

Agent files follow this naming pattern:
- `{domain}.agent.md` - Clear, descriptive name
- Examples: `python-backend.agent.md`, `frontend.agent.md`

## Creating New Agents

To create a new custom agent:

1. Create a new `.agent.md` file in this directory
2. Use YAML frontmatter for metadata:
```yaml
---
name: agent_name
description: Brief description of agent expertise
tools: ["*"]  # or specific tools
target: github-copilot
metadata:
  maintainer: eventrelay-team
  version: 1.0.0
  domains: [domain1, domain2]
---
```
3. Add detailed instructions, examples, and best practices
4. Document boundaries and when to use the agent

## Best Practices

### For Agent Creators

1. **Be Specific**: Focus on a clear domain of expertise
2. **Provide Examples**: Include concrete code examples
3. **Set Boundaries**: Define what the agent should and shouldn't do
4. **Stay Current**: Update agents when patterns change
5. **Test Thoroughly**: Verify examples work correctly

### For Agent Users

1. **Choose the Right Agent**: Select based on your task
2. **Provide Context**: Give agents enough information
3. **Review Suggestions**: Always review agent recommendations
4. **Provide Feedback**: Help improve agents over time

## Common Agent Patterns

All EventRelay agents follow these patterns:

### Standard Test Video ID
**ALWAYS use**: `auJzb1D-fag`
**NEVER use**: `dQw4w9WgXcQ`

### Error Handling
- Comprehensive try-except blocks
- Proper logging with structlog
- Appropriate HTTP status codes

### Type Safety
- Python: Type hints on all functions
- TypeScript: Strict mode enabled
- Validation with Pydantic

### Testing
- >80% code coverage target
- Use real filesystems (not mocks)
- Clean up temporary resources

### Documentation
- Docstrings for all public functions
- Clear, concise language
- Working code examples

## EventRelay Core Workflow

All agents understand EventRelay's single workflow:

1. **Paste YouTube Link** → User provides URL
2. **Extract Context** → Transcribe video, extract events
3. **Spawn Agents** → Dispatch based on events
4. **Run Tasks** → Execute real-world actions
5. **Publish Outputs** → Deliver results

**Important**: No manual triggers, no alternative workflows.

## Troubleshooting

### Agent Not Responding
- Check agent file has valid YAML frontmatter
- Verify agent name matches file name
- Ensure description is clear and specific

### Wrong Agent Selected
- Be more specific in your question
- Explicitly mention the agent: `@agent-name`
- Check file context (Python file → backend agent)

### Agent Gives Incorrect Advice
- Verify agent instructions are current
- Update agent file with correct patterns
- Check project conventions haven't changed

## Agent Self-Creation System

EventRelay includes an **automated agent gap detection and recommendation system** that identifies when new custom agents would be beneficial.

### How It Works

1. **Monitors** usage patterns and identifies domains without agent coverage
2. **Analyzes** frequency and confidence of detected gaps
3. **Recommends** new agents when thresholds are met
4. **Generates** production-ready agent templates for review

### Using the System

```bash
# Analyze current agent coverage
python scripts/manage_custom_agents.py analyze --demo

# Get recommendations for new agents
python scripts/manage_custom_agents.py recommend

# Generate agent template
python scripts/manage_custom_agents.py generate infrastructure

# Full analysis report
python scripts/manage_custom_agents.py report

# List and validate existing agents
python scripts/manage_custom_agents.py list
python scripts/manage_custom_agents.py validate
```

### Example Workflow

1. **Detection**: System detects repeated work in infrastructure domain
2. **Recommendation**: Suggests creating infrastructure agent (confidence: 0.85)
3. **Generation**: Creates template with YAML frontmatter and best practices
4. **Review**: Human reviews and refines the generated template
5. **Activation**: Move to `.github/agents/` and commit
6. **Usage**: `@infrastructure` now available in GitHub Copilot

### Documentation

See `/docs/AGENT_SELF_CREATION.md` for comprehensive documentation on:
- How the system detects gaps
- Recommendation thresholds and priorities
- Template generation details
- Integration and monitoring options
- FAQ and troubleshooting

### Demo

Run the interactive demo:
```bash
python examples/agent_self_creation_demo.py
```

## Contributing

When updating agents:

1. Review existing agent patterns
2. Test changes with real scenarios
3. Update version number in metadata
4. Document significant changes
5. Commit with clear message

When creating new agents:
1. Use `manage_custom_agents.py` to check for recommendations
2. Generate template or create from scratch
3. Follow existing agent patterns
4. Validate with `python scripts/manage_custom_agents.py validate`
5. Test with sample queries before committing

## Resources

- **GitHub Copilot Docs**: https://docs.github.com/en/copilot
- **Custom Agents Guide**: https://docs.github.com/en/copilot/how-tos/use-copilot-agents
- **Project README**: `/README.md`
- **Architecture Guide**: `/docs/CLAUDE.md`
- **Copilot Instructions**: `/.github/copilot-instructions.md`

## Support

For issues or questions about custom agents:
1. Check agent documentation in the `.agent.md` files
2. Review project documentation in `/docs`
3. Open an issue on GitHub
4. Contact the EventRelay team

---

**Remember**: Custom agents are here to help you follow EventRelay's best practices and maintain code quality. Use them frequently and provide feedback to improve them!
