# AGENTS.md

## Mission
To enable autonomous AI agents to efficiently reason, plan, and execute tasks within this repository, specifically focusing on the integration and orchestration of Model Context Protocol (MCP) servers and Video Intelligence pipelines.

## Scope of "Actionable Room"
Agents are granted permission and encouraged to:
1.  **Modify and Expand `mcp-servers/`**: Create new MCP servers, update existing ones, and refactor code to improve modularity and performance.
2.  **Improve Automation**: Create and edit GitHub Actions workflows (`.github/workflows/`) to add robust testing and verification for new features.
3.  **Refactor for Clarity**: Improve documentation (READMEs) and code structure to facilitate better "Machine Readability" and "Human Understandability".

## Protocols
1.  **Verify Before Submit**:
    - Always run relevant verification scripts or tests before submitting changes.
    - If no test exists for a new feature, **create one**.
2.  **CI/CD Alignment**:
    - Ensure all changes pass existing CI checks.
    - When adding a new component (like an MCP server), add a corresponding CI workflow to ensure it remains functional.
3.  **Cross-Platform Compatibility**:
    - Write code that is compatible with Linux and Windows environments whenever possible (e.g., handling `asyncio` loops correctly).
4.  **Documentation**:
    - Update `README.md` files when interface changes occur.
    - Document limitations (e.g., "Text-only CLI wrapper") clearly.
