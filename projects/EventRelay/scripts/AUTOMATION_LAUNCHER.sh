#!/bin/bash

# Universal Video-to-Action Platform - Automation Suite (Canonical)
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$BASE_DIR/.." >/dev/null 2>&1 && pwd)"
UVAI_ROOT="$(cd "$PROJECT_ROOT/../../.." >/dev/null 2>&1 && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

echo "🚀 UNIVERSAL VIDEO-TO-ACTION PLATFORM - AUTOMATION SUITE"
echo "========================================================"

ensure_env() {
  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi
  source "$VENV_DIR/bin/activate"
  pip install -q -e "$PROJECT_ROOT[youtube,ml,postgres]"
}

echo ""
echo "📋 AVAILABLE AUTOMATION WORKFLOWS:"
echo "  1. 🏗️  Launch Development Backend (FastAPI)"
echo "  2. 🎬 Process YouTube Video (Real)"
echo "  3. 🧠 State Awareness Check (MCP verify)"
echo "  4. 🧭 Start MCP Ecosystem"
echo "  5. 🧪 Integration Testing Pipeline"
echo "  6. 🎯 Run All (verify → backend → sample process)"
echo "  0. ❌ Exit"
echo ""

read -p "Select workflow (0-6): " choice

case $choice in
  1)
    echo "🏗️ Launching Development Backend..."
    ensure_env
    exec python "$PROJECT_ROOT/src/youtube_extension/cli.py" serve --host 0.0.0.0 --port 8000 --reload
    ;;
  2)
    read -p "🎬 Enter YouTube URL: " video_url
    if [[ -z "${video_url// }" ]]; then
      echo "❌ No URL provided"; exit 1
    fi
    echo "🎥 Processing video with REAL pipeline..."
    ensure_env || true
    exec python "$UVAI_ROOT/scripts/REAL_live_video_processor.py" "$video_url"
    ;;
  3)
    echo "🧠 Verifying MCP Ecosystem state..."
    python "$UVAI_ROOT/mcp-ecosystem/start_ecosystem.py" --verify
    ;;
  4)
    echo "🧭 Starting MCP Ecosystem..."
    python "$UVAI_ROOT/mcp-ecosystem/start_ecosystem.py"
    ;;
  5)
    echo "🧪 Running Integration Tests..."
    ensure_env
    pip install -q -e "$PROJECT_ROOT[dev]"
    cd "$PROJECT_ROOT"
    exec python -m pytest tests/integration/test_video_processing_pipeline.py -q || true
    ;;
  6)
    echo "🎯 Running verification, backend, and sample processing..."
    python "$UVAI_ROOT/mcp-ecosystem/start_ecosystem.py" --verify || true
    ensure_env
    ( python "$PROJECT_ROOT/src/youtube_extension/cli.py" serve --host 0.0.0.0 --port 8000 --reload & )
    sleep 3
    curl -s -X POST http://localhost:8000/api/process-video-markdown \
      -H "Content-Type: application/json" \
      -d '{"video_url":"https://www.youtube.com/watch?v=jNQXAC9IVRw"}' | head -c 800 || true
    echo
    ;;
  0)
    echo "❌ Exiting automation suite"; exit 0 ;;
  *)
    echo "❌ Invalid selection"; exit 1 ;;
esac

echo ""
echo "🎉 Automation workflow completed!"
