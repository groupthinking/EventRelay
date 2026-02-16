#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
FRONTEND_DIR="${REPO_ROOT}/frontend"

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "[error] Frontend directory not found at ${FRONTEND_DIR}" >&2
  exit 1
fi

cd "${FRONTEND_DIR}"

if ! command -v npm >/dev/null 2>&1; then
  echo "[error] npm is required but not found in PATH" >&2
  exit 1
fi

echo "[step] Installing frontend dependencies (npm install)"
npm install

PORT=${PORT:-3000}
echo "[step] Starting React dev server on http://localhost:${PORT}"
PORT=${PORT} npm start
