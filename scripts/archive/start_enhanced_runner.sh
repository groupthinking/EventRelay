#!/bin/bash
# Enhanced Continuous Runner Startup Script

echo "🚀 Starting Llama Background Agent Enhanced Runner..."

# Set environment variables
export USE_LLAMA=true
export BATCH_SIZE=10
export SLEEP_INTERVAL=60

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
export PYTHONPATH="${REPO_ROOT}"

# Start the enhanced runner
python3 scripts/enhanced_continuous_runner.py
