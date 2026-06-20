#!/bin/bash
#
# Start the YouTube-extension backend / MCP endpoint on port 8010.
# This makes the agent network's "real" HTTP tool path live
# (http://127.0.0.1:8010/process_video_markdown etc.).
#
# Part of Ralph Loop for "Grok Agent picks best on recommendation
# for EventRelay agent pipeline completion" (completion promise "max").
#
# Usage:
#   bash scripts/start_mcp_youtube.sh          # start in background, wait for ready
#   bash scripts/start_mcp_youtube.sh stop     # stop
#
# After start, re-run:
#   python scripts/testing/run_orchestrator.py --video-id ftBWgcwvEk4
# (the HTTP call in the network will now hit the live server)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT=8010
LOG_DIR="logs"
LOG_FILE="$LOG_DIR/mcp_youtube.log"
PID_FILE="$LOG_DIR/mcp_youtube.pid"

mkdir -p "$LOG_DIR"

UVICORN_BIN=".venv/bin/uvicorn"
if [[ ! -x "$UVICORN_BIN" ]]; then
  UVICORN_BIN="python -m uvicorn"
fi

APP_MODULE="src.youtube_extension.main:app"

stop_server() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "Stopping MCP YouTube server (pid $pid)..."
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  # Also kill any uvicorn on the port as safety
  lsof -ti :$PORT | xargs kill -9 2>/dev/null || true
}

start_server() {
  stop_server

  echo "Starting YouTube MCP / backend server on 127.0.0.1:$PORT ..."
  echo "  App: $APP_MODULE"
  echo "  Log: $LOG_FILE"

  # Use nohup so it survives the shell
  nohup $UVICORN_BIN "$APP_MODULE" \
    --host 127.0.0.1 \
    --port "$PORT" \
    --log-level info \
    > "$LOG_FILE" 2>&1 &

  local pid=$!
  echo "$pid" > "$PID_FILE"

  # Wait for port to be ready (up to ~30s)
  echo -n "Waiting for server to be ready"
  for i in $(seq 1 30); do
    if curl -s --max-time 1 "http://127.0.0.1:$PORT/docs" >/dev/null 2>&1 || \
       curl -s --max-time 1 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 || \
       curl -s --max-time 1 "http://127.0.0.1:$PORT/openapi.json" >/dev/null 2>&1; then
      echo " OK (pid $pid)"
      echo "Server is live at http://127.0.0.1:$PORT"
      echo "To stop: bash scripts/start_mcp_youtube.sh stop"
      echo "Logs: tail -f $LOG_FILE"
      return 0
    fi
    echo -n "."
    sleep 1
  done

  echo " FAILED to become ready. Check $LOG_FILE"
  stop_server
  return 1
}

case "${1:-start}" in
  start|"")
    start_server
    ;;
  stop)
    stop_server
    echo "Stopped."
    ;;
  restart)
    stop_server
    start_server
    ;;
  status)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      echo "Running (pid $(cat "$PID_FILE")) on port $PORT"
    else
      echo "Not running"
    fi
    ;;
  *)
    echo "Usage: $0 [start|stop|restart|status]"
    exit 1
    ;;
esac
