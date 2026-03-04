#!/bin/bash
# Launches Google Chrome with remote debugging enabled for NotebookLM automation.

# Default macOS Chrome path
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# Use a specific profile directory in the project root to keep sessions isolated but persistent
USER_DATA_DIR="$(pwd)/notebooklm_chrome_profile"
PORT=9222

if [ ! -f "$CHROME_PATH" ]; then
    echo "Error: Google Chrome not found at $CHROME_PATH"
    exit 1
fi

echo "Launching Chrome for NotebookLM..."
echo "User Data Dir: $USER_DATA_DIR"
echo "Debugging Port: $PORT"

# Launch Chrome in background (single line to avoid shell parsing issues)
"$CHROME_PATH" --remote-debugging-port=$PORT --user-data-dir="$USER_DATA_DIR" --no-first-run --no-default-browser-check "https://notebooklm.google.com/" &

echo "----------------------------------------------------------------"
echo "Chrome launched!" 
echo "1. Please log in to Google NotebookLM in the opened window."
echo "2. Once logged in, run your ingestion script."
echo "----------------------------------------------------------------"