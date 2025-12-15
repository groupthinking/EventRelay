#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/Dev/OpenAI_Hub"
echo "== Hub Health @ $(date)"
echo "-- Node"
which node; node -v
echo "-- Codex"
which codex; codex --version || true
echo "-- Config"
grep -n 'runtime_root\|project_roots' "$HOME/.codex/config.toml" || true
echo "-- Symlinks"
find "$ROOT" -maxdepth 2 -type l -exec bash -lc 'printf "%s -> %s\n" "{}" "$(readlink "{}")"' \;
echo "-- Missing targets"
while IFS= read -r link; do tgt="$(readlink "$link")"; [[ -e "$tgt" ]] || echo "MISSING: $link -> $tgt"; done < <(find "$ROOT" -maxdepth 2 -type l)
echo "-- Env dirs"
ls -ld "$ROOT/configs/envs" "$ROOT/keys" || true
