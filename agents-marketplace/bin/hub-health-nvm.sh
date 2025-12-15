#!/bin/zsh
set -euo pipefail
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use v22.16.0 >/dev/null
exec "$HOME/Dev/OpenAI_Hub/bin/hub-health.sh"
