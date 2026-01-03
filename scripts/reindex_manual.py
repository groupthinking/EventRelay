import os

ROOT_DIR = os.getcwd()
INDEX_FILE = os.path.join(ROOT_DIR, "shared/repo_index.txt")

IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'dist', 'build', '.venv',
    'venv', 'coverage', '.idea', '.vscode', 'tmp', 'logs',
    'mcp-servers/gcp-vector-db/build', '.gemini',
    '.venv_prod_verify', 'ai-edge-torch', 'video_representations_extractor-1.14.0',
    '.mypy_cache', '.ruff_cache', '.pytest_cache'
}

IGNORE_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.class', '.jar',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.mp4', '.avi',
    '.mov', '.mp3', '.wav', '.zip', '.tar', '.gz', '.7z', '.pdf',
    '.exe', '.bin', '.lock', 'package-lock.json', 'yarn.lock'
}

def should_ignore(path):
    parts = path.split(os.sep)
    for part in parts:
        if part in IGNORE_DIRS:
            return True

    _, ext = os.path.splitext(path)
    if ext.lower() in IGNORE_EXTENSIONS:
        return True

    return False

def get_description(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and len(line) < 200:
                    return line
            return "[Empty or binary]"
    except Exception:
        return "[Error reading]"

def main():
    print(f"Indexing {ROOT_DIR} to {INDEX_FILE}...")

    with open(INDEX_FILE, 'w', encoding='utf-8') as index:
        index.write(f"# Repository Index - Generated automatically\n")
        index.write(f"# Format: Path | Description\n\n")

        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                filepath = os.path.join(root, file)
                relpath = os.path.relpath(filepath, ROOT_DIR)

                if should_ignore(filepath):
                    continue

                desc = get_description(filepath)
                index.write(f"{relpath} | {desc}\n")

    print(f"Index created at {INDEX_FILE}")

if __name__ == "__main__":
    main()
