#!/bin/zsh
set -euo pipefail

ROOT="$HOME/Dev/OpenAI_Hub"
CODE="$HOME/Code"
CFG="$HOME/.codex/config.toml"
HUBIGNORE="$ROOT/.hubignore"

dryrun=false
[[ "${1:-}" == "--dry-run" ]] && dryrun=true

should_ignore() {
  local name="$1"
  [[ -f "$HUBIGNORE" ]] || return 1
  while IFS= read -r pat; do
    [[ -z "$pat" || "$pat" == \#* ]] && continue
    [[ "$name" == $~pat ]] && return 0
  done < "$HUBIGNORE"
  return 1
}

exists_link() {
  local src="$1"
  local found=0
  for lnk in "${(@f)$(find "$ROOT" -maxdepth 2 -type l 2>/dev/null)}"; do
    [[ "$(readlink "$lnk")" == "$src" ]] && { found=1; break; }
  done
  [[ $found -eq 1 ]]
}

echo "== Hub Sync ($(date))"
echo "-- Source: $CODE"
echo "-- Hub:    $ROOT"

echo "-- Pruning broken symlinks"
for lnk in "${(@f)$(find "$ROOT" -maxdepth 2 -type l 2>/dev/null)}"; do
  tgt="$(readlink "$lnk" || true)"
  if [[ -n "$tgt" && ! -e "$tgt" ]]; then
    echo "   MISSING -> $lnk -> $tgt"
    $dryrun || rm -f -- "$lnk"
  fi
done

echo "-- Linking new ~/Code/* into projects/"
mkdir -p "$ROOT/projects"
for d in "${(@f)$(find "$CODE" -maxdepth 1 -mindepth 1 -type d -not -name '.*' 2>/dev/null | sort)}"; do
  name="${d:t}"  # basename
  if should_ignore "$name"; then
    echo "   SKIP (ignored): $name"
    continue
  fi
  if exists_link "$d"; then
    echo "   OK (already linked): $name"
  else
    dest="$ROOT/projects/$name"
    echo "   ADD link: $dest -> $d"
    $dryrun || ln -snf -- "$d" "$dest"
  fi
done

echo "-- Reindexing project_roots in $CFG"
links=("${(@f)$(find "$ROOT" -maxdepth 2 -type l 2>/dev/null | sort)}")
tmp="$CFG.tmp.$$"
{
  # keep everything except existing project_roots block
  awk '
    BEGIN{skip=0}
    /^project_roots *= *\[/ {skip=1; next}
    skip && /\]/ {skip=0; next}
    skip==0 {print}
  ' "$CFG"

  echo 'project_roots = ['
  first=1
  for lnk in "${links[@]}"; do
    tgt="$(readlink "$lnk")"
    [[ -z "$tgt" ]] && continue
    (( first )) || echo ","
    printf '  "%s"' "$tgt"
    first=0
  done
  echo
  echo ']'
} > "$tmp"

if $dryrun; then
  echo "   (dry-run) would write updated project_roots to $CFG"
  rm -f "$tmp"
else
  mv "$tmp" "$CFG"
  echo "   wrote new project_roots to $CFG"
fi

echo "-- Done."
