# Contributing to EventRelay

We welcome contributions to EventRelay! Please follow these guidelines to ensure a smooth process.

## Getting Started

1.  **Fork the repository** and clone it locally.
2.  **Set up your environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .[dev,youtube,ml]
    npm install                        # installs all monorepo workspaces
    ```
3.  **Start the services**:
    ```bash
<<<<<<< HEAD
    # Terminal 1 — backend
    uvicorn src.youtube_extension.main:app --reload --port 8000
=======
    # Terminal 1 — backend (PYTHONPATH=src is required; see CLAUDE.md)
    PYTHONPATH=src uvicorn youtube_extension.main:app --reload --port 8000
>>>>>>> origin/main
    # Terminal 2 — frontend
    turbo run dev
    ```
4.  **Create a branch** for your feature or fix:
    ```bash
    git checkout -b feature/my-feature
    ```

## Parallel Development with Git Worktrees

EventRelay uses multi-agent workflows extensively. When working on multiple branches simultaneously (e.g., testing a new MCP server while fixing a pipeline bug), use **git worktrees** instead of repeated stash/switch cycles:

```bash
# Create a linked worktree for a second branch — no stashing needed
git worktree add ../EventRelay-mcp-dev feature/mcp-enhancement

# List active worktrees
git worktree list

# Remove when done (branch is preserved)
git worktree remove ../EventRelay-mcp-dev
```

GitHub Desktop 3.6+ has a built-in worktree switcher in the top toolbar. Copilot coding agents also spin up worktrees automatically for isolated parallel sessions — the same model applies to manual development.

## Development Standards

*   **Real Implementation Only**: We enforce a `REAL_MODE_ONLY` policy. Do not commit simulated code (e.g., `asyncio.sleep` for fake delays, hardcoded responses).
*   **Security First**:
    *   Never commit secrets.
    *   Validate all inputs.
    *   Do not use `dangerouslySetInnerHTML` in React.
    *   Use `subprocess` carefully with sanitized inputs.
*   **Testing**:
    *   Run backend tests: `pytest tests/`
    *   Run frontend tests: `turbo run test`
    *   Ensure all tests pass before submitting a PR.

## Pull Request Process

1.  **Description**: Clearly describe your changes and the problem they solve.
2.  **Verification**: Include steps to verify your changes.
3.  **CI/CD**: Ensure all CI checks pass (Security Scan, Tests).

## Code of Conduct

Please be respectful and professional in all interactions.
