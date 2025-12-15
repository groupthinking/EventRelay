# CodeQL Security Scanning Configuration

## Overview

This document explains the CodeQL security scanning configuration for EventRelay and why certain directories are excluded from analysis.

## Configuration File

The CodeQL configuration is defined in `.github/codeql/codeql-config.yml` and is used by the security scanning workflow in `.github/workflows/security.yml`.

## Excluded Paths

The following paths are excluded from CodeQL analysis:

### Auto-Generated Projects (`generated_projects/**`)
- **Reason**: Contains auto-generated Next.js demo projects created by the EventRelay system
- **Issue**: These files contain intentional placeholder comments like "Error generating..." that are not valid TypeScript/JavaScript syntax
- **Impact**: These syntax errors cause CodeQL scanning to fail
- **Solution**: Exclude from scanning as they are demonstration artifacts, not production code

### Research Archives (`research/labs/archive/**`)
- **Reason**: Contains archived experimental code and research artifacts
- **Issue**: May contain incomplete or experimental code with syntax errors
- **Impact**: Not part of the production codebase
- **Solution**: Exclude from scanning as they are archived experiments

### MCP Bridge (`src/mcp-bridge.py`)
- **Reason**: Contains import statements referencing non-standard module paths
- **Issue**: Imports like `from unified-ai-sdk.rate_limiter` use hyphens which cause parsing issues
- **Impact**: This is an experimental integration file
- **Solution**: Exclude from scanning until the module structure is standardized

## Scanned Paths

The following paths are analyzed by CodeQL (as they are not excluded):

- `src/**` - Core Python backend code
- `frontend/**` - React TypeScript frontend application
- `scripts/**` - Utility scripts and tools
- `tests/**` - Test suite
- `development/**` - Development agents and tools

## Git Ignore

The `.gitignore` file has been updated to prevent these auto-generated directories from being committed:

```gitignore
# Auto-generated projects (keep execution_workspace as it has learning content)
generated_projects/
research/labs/archive/
```

This ensures:
1. Auto-generated files don't pollute the repository
2. CodeQL doesn't scan files that aren't committed
3. The repository remains focused on production code

## Maintenance

When adding new directories that should be excluded from CodeQL scanning:

1. Update `.github/codeql/codeql-config.yml` with the new path pattern
2. Update `.gitignore` if the directory shouldn't be committed
3. Document the reason in this file

## Related Issues

- Issue #31: TypeScript/JavaScript syntax errors in auto-generated projects
- PR #32: Configure CodeQL to exclude auto-generated artifacts from scanning

## Testing

To verify the CodeQL configuration works correctly:

1. The security workflow should complete without syntax errors
2. CodeQL should only analyze files in the included paths
3. Auto-generated projects should not appear in security alerts

## References

- [CodeQL Configuration Documentation](https://docs.github.com/en/code-security/code-scanning/automatically-scanning-your-code-for-vulnerabilities-and-errors/customizing-code-scanning)
- [GitHub CodeQL Action](https://github.com/github/codeql-action)
