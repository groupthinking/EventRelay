#!/usr/bin/env bash
set -euo pipefail
[ $# -gt 0 ] || { echo "Usage: codex-batch.sh \$'RUN:\\n- which node\\n- node -v'"; exit 2; }
PAYLOAD="$1"
if command -v gtimeout >/dev/null 2>&1; then
  gtimeout 10s bash -lc "printf '%b' \"$PAYLOAD\" | script -q /dev/null codex"
else
  script -q /dev/null codex <<EOF
$PAYLOAD
EOF
fi
