# Claude AI Instructions - EventRelay

This file provides guidance for Claude AI when working with the EventRelay codebase.

For comprehensive instructions, please refer to:
- `/docs/CLAUDE.md` - Detailed Claude.MD Master Intelligence Framework
- `/.claude/claude_instructions.md` - Code-specific instructions
- `/.github/copilot-instructions.md` - GitHub Copilot instructions (also useful for Claude)

## Quick Reference

### Critical Rules
1. **Test Video ID**: Always use `auJzb1D-fag` for test data
2. **No Hardcoded Secrets**: Use environment variables
3. **Minimal Changes**: Make surgical, precise modifications
4. **Test First**: Run tests before claiming completion
5. **No Mock Filesystems**: Use real temporary directories

### Architecture
- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React with TypeScript
- **Agent Framework**: MCP/A2A workflows
- **AI Models**: Gemini, OpenAI, Anthropic

### Common Tasks
- **Run Backend**: `uvicorn uvai.api.main:app --reload --port 8000`
- **Run Frontend**: `npm start --prefix frontend`
- **Run Tests**: `pytest tests/ -v --cov`
- **Format Code**: `black . && ruff check . --fix`

See the referenced files above for complete guidance.

# CLAUDE.md - Repository Analysis Configuration

## Project Context

This is a [PROJECT_TYPE] codebase requiring comprehensive audit and production transformation.

**Primary Stack:** [LANGUAGES/FRAMEWORKS]
**Target State:** Production-ready, enterprise-grade deployment

## Code Conventions

### Style Requirements
- Follow existing patterns in `src/` directory
- Use TypeScript strict mode / Python type hints / equivalent
- All functions require JSDoc/docstring documentation
- Maximum file length: 500 lines
- Maximum function length: 50 lines

### Error Handling
- Never swallow errors silently
- Use structured error types with error codes
- All async operations require error handling
- Log errors with correlation IDs

### Security Requirements
- NO hardcoded secrets - use environment variables
- ALL user input must be validated and sanitized
- Database queries must use parameterized statements
- Authentication required for all non-public endpoints

## Analysis Focus Areas

When reviewing this codebase, prioritize:

1. **Security vulnerabilities** - Injection, auth bypass, data exposure
2. **Duplicate code** - DRY violations affecting maintainability
3. **Error handling gaps** - Unhandled exceptions, silent failures
4. **Performance issues** - N+1 queries, memory leaks, blocking operations
5. **Dead code** - Unreachable code, unused exports

## Workflow Instructions

### Before Making Changes
1. Run existing tests to establish baseline
2. Document current behavior
3. Identify all affected modules

### When Making Changes
1. One logical change per commit
2. Update tests before implementation
3. Update documentation alongside code

### After Making Changes
1. Run full test suite
2. Verify no new linting errors
3. Check for security regressions

## Sub-Agent Strategy

Use dedicated sub-agents for:
- **Security Review**: Isolated context, fresh perspective on vulnerabilities
- **Architecture Analysis**: Dependency mapping, module relationships
- **Performance Audit**: Query analysis, memory profiling
- **Test Coverage**: Gap identification, edge case discovery

## File Exploration Strategy

```
Start broad: Understand module boundaries first
Go deep: Trace specific flows end-to-end
Cross-reference: Identify shared dependencies
Document: Map what you learn to ARCHITECTURE.md
```

## Known Issues to Track

<!-- Update this section as issues are discovered -->

- [ ] Issue 1: [Description]
- [ ] Issue 2: [Description]

## Testing Requirements

- Unit tests for all business logic
- Integration tests for API endpoints
- Security tests for auth flows
- Performance benchmarks for critical paths

## Deployment Checklist

Before marking production-ready:
- [ ] All CRITICAL security issues resolved
- [ ] Error handling complete
- [ ] Logging and monitoring configured
- [ ] Health checks implemented
- [ ] Documentation updated
- [ ] CI/CD pipeline passing
