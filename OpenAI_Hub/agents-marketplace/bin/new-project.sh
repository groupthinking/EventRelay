
set -euo pipefail

usage() {
  cat >&2 <<USAGE
Usage:
  new-project.sh <node|python> <abs-target-dir> [hub-category] [hub-name]

Examples:
  new-project.sh node   /Users/$USER/Code/my-app           projects my-app
  new-project.sh python /Users/$USER/Code/my-agent         agents   my-agent

Notes:
  - hub-category defaults to 'projects' if omitted.
  - hub-name defaults to basename of abs-target-dir if omitted.
  - Requires: npm (for node), python3 (for python), and ~/Dev/OpenAI_Hub/bin/hub-add.sh
USAGE
  exit 2
}

LANGUAGE="${1:-}"; TARGET="${2:-}"; CATEGORY="${3:-projects}"
[ -n "${LANGUAGE}" ] && [ -n "${TARGET}" ] || usage
NAME="${4:-$(basename "$TARGET")}"

ROOT="$HOME/Dev/OpenAI_Hub"
HUB_ADD="$ROOT/bin/hub-add.sh"
[ -x "$HUB_ADD" ] || { echo "Missing $HUB_ADD" >&2; exit 1; }

mkdir -p "$TARGET"
cd "$TARGET"

case "$LANGUAGE" in
  node)
    # Node project scaffold
    npm init -y >/dev/null
    npm i -D typescript tsx >/dev/null
    npm i dotenv >/dev/null

    # tsconfig + src
    mkdir -p src
    cat > tsconfig.json <<'JSON'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "skipLibCheck": true,
    "outDir": "dist"
  },
  "include": ["src"]
}
JSON

    cat > src/index.ts <<'TS'
import 'dotenv/config';

async function main() {
  const key = process.env.OPENAI_API_KEY ? 'present' : 'missing';
  console.log(`OpenAI API key is ${key}. Ready to build.`);
}

main().catch(err => { console.error(err); process.exit(1); });
TS

    # package scripts
    jq '.scripts |= (. + {"dev":"tsx src/index.ts","build":"tsc","start":"node dist/index.js"})' package.json > package.tmp.json && mv package.tmp.json package.json || true

    ;;

  python)
    # Python project scaffold
    python3 -m venv .venv
    . .venv/bin/activate
    python3 -m pip install --upgrade pip >/dev/null
    python3 -m pip install openai python-dotenv >/dev/null

    mkdir -p src
    cat > src/main.py <<'PY'
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    print(f"OpenAI API key is {'present' if os.getenv('OPENAI_API_KEY') else 'missing'}. Ready to build.")

if __name__ == "__main__":
    main()
PY
    deactivate
    ;;

  *)
    echo "Unknown language: $LANGUAGE" >&2; usage;;
esac

# env + git hygiene
cat > .env <<'ENV'
# Fill me before running:
OPENAI_API_KEY=
ENV
chmod 600 .env

cat > .gitignore <<'GI'
node_modules
dist
.venv
.env
.DS_Store
GI

git init -q || true

# Register in hub + Codex config
"$HUB_ADD" "$TARGET" "$CATEGORY" "$NAME"

echo "✅ Created $LANGUAGE project at $TARGET"
echo "   Registered in Hub: $ROOT/$CATEGORY/$NAME"
echo "   Next:"
if [ "$LANGUAGE" = "node" ]; then
  echo "     1) echo 'OPENAI_API_KEY=sk-...' >> $TARGET/.env"
  echo "     2) cd $TARGET && npm run dev"
else
  echo "     1) echo 'OPENAI_API_KEY=sk-...' >> $TARGET/.env"
  echo "     2) cd $TARGET && . .venv/bin/activate && python3 src/main.py"
fi

