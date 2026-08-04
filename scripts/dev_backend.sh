#!/usr/bin/env bash
# Local FastAPI backend for EventRelay (F6 + F7).
#
# - Defaults ALLOW_UNAUTHENTICATED=1 when EVENTRELAY_API_KEY is unset so protected
#   routes are reachable without 503 fail-closed (never use this in production).
# - Reminds you to install the youtube extra when yt-dlp / youtube-transcript-api
#   are missing.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if [[ -z "${EVENTRELAY_API_KEY:-}" && -z "${ALLOW_UNAUTHENTICATED:-}" ]]; then
  export ALLOW_UNAUTHENTICATED=1
  echo "dev_backend: ALLOW_UNAUTHENTICATED=1 (local fail-open; set EVENTRELAY_API_KEY to require X-API-Key)"
fi

python - <<'PY' || true
import importlib.util
missing = [n for n in ("yt_dlp", "youtube_transcript_api") if importlib.util.find_spec(n) is None]
if missing:
    print(
        "dev_backend: missing video packages "
        + ", ".join(missing)
        + ' — install with: pip install -e ".[dev,youtube]"'
    )
else:
    print("dev_backend: yt_dlp + youtube_transcript_api available")
PY

export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}src"
exec python -m uvicorn youtube_extension.main:app --host 127.0.0.1 --port "${PORT:-8000}" --reload
