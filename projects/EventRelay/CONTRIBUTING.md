# Contributing to EventRelay

We welcome contributions to EventRelay! Please follow these guidelines to ensure a smooth process.

## Getting Started

1.  **Fork the repository** and clone it locally.
2.  **Set up your environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -e .[dev]
    npm install --prefix frontend
    ```
3.  **Create a branch** for your feature or fix:
    ```bash
    git checkout -b feature/my-feature
    ```

## Development Standards

*   **Real Implementation Only**: We enforce a `REAL_MODE_ONLY` policy. Do not commit simulated code (e.g., `asyncio.sleep` for fake delays, hardcoded responses).
*   **Security First**:
    *   Never commit secrets.
    *   Validate all inputs.
    *   Do not use `dangerouslySetInnerHTML` in React.
    *   Use `subprocess` carefully with sanitized inputs.
*   **Testing**:
    *   Run backend tests: `pytest tests/`
    *   Run frontend tests: `npm test --prefix frontend`
    *   Ensure all tests pass before submitting a PR.

## Pull Request Process

1.  **Description**: Clearly describe your changes and the problem they solve.
2.  **Verification**: Include steps to verify your changes.
3.  **CI/CD**: Ensure all CI checks pass (Security Scan, Tests).

## Code of Conduct

Please be respectful and professional in all interactions.
