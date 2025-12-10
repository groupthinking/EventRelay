#!/bin/bash
# Start Chrome with isolated profile to avoid Playwright conflicts

echo "Starting Chrome with isolated profile..."

# Check if Chrome is installed
if [ -d "/Applications/Google Chrome.app" ]; then
    CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif [ -d "/Applications/Chrome.app" ]; then
    CHROME_PATH="/Applications/Chrome.app/Contents/MacOS/Chrome"
else
    echo "Error: Chrome not found in standard locations"
    exit 1
fi

# Create isolated profile directory if it doesn't exist
PROFILE_DIR="$HOME/ChromePersonal"
mkdir -p "$PROFILE_DIR"

# Launch Chrome with isolated profile
"$CHROME_PATH" \
    --user-data-dir="$PROFILE_DIR" \
    --disable-blink-features=AutomationControlled \
    --excludeSwitches=enable-automation \
    --disable-infobars \
    --no-first-run \
    --no-default-browser-check &

echo "Chrome started with isolated profile at: $PROFILE_DIR"
echo "This instance should not be affected by Playwright timeouts"
