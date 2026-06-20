#!/usr/bin/env bash
set -euo pipefail
# Lightweight wrapper to run pytest in a minimal environment to avoid leaking
# local API keys or credentials into tests (useful for local development).
# Usage: ./bin/run_tests_clean.sh [pytest-args...]

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTEST="$REPO_ROOT/.venv/bin/pytest"

if [ ! -x "$PYTEST" ]; then
  echo "ERROR: pytest not found at $PYTEST. Activate your virtualenv or create .venv."
  exit 2
fi

# Minimal environment: keep PATH and HOME; set PYTHONPATH to repo root so imports work
env -i PATH=/usr/bin:/bin HOME="$HOME" LANG=en_US.UTF-8 \
    PYTHONPATH="$REPO_ROOT" GEMINI_MODEL=gemini-2.5-flash \
    "$PYTEST" "$@"
