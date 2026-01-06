#!/usr/bin/env python3
"""Direct SQL ingestion script that bypasses MCP server for RAG indexing."""
import os
import json
import time
import psycopg2
from typing import List
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

# Configuration
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found")
    exit(1)

genai.configure(api_key=GOOGLE_API_KEY)
EMBEDDING_MODEL = "models/text-embedding-004"

# Database connection
DATABASE_URL = os.environ.get("VECTOR_DATABASE_URL") or os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("Error: No DATABASE_URL found")
    exit(1)

ROOT_DIR = os.getcwd()

IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'dist', 'build', '.build', '.venv',
    'venv', 'coverage', '.idea', '.vscode', 'tmp', 'logs', 'Gemini_Brain', '.gemini',
    '.venv_prod_verify', 'ai-edge-torch', 'video_representations_extractor-1.14.0',
    '.mypy_cache', '.ruff_cache', '.pytest_cache', 'projects', 'examples', '_archive',
    'supabase', 'youtube_processed_videos', 'mcp-servers'
}

IGNORE_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.class', '.jar',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.mp4', '.avi',
    '.mov', '.mp3', '.wav', '.zip', '.tar', '.gz', '.7z', '.pdf',
    '.exe', '.bin', '.lock', 'package-lock.json', 'yarn.lock', '.rtf',
    '.db', '.sqlite', '.sqlite3', '.log', '.whl'
}

MAX_FILE_SIZE = 100 * 1024


def get_embedding(text: str) -> List[float]:
    """Get Gemini embedding for text."""
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
        title="Code Snippet"
    )
    return result['embedding']


def should_ignore(relpath: str, abspath: str) -> bool:
    """Check if file should be ignored."""
    parts = relpath.split(os.sep)
    for part in parts:
        if part in IGNORE_DIRS:
            return True
    _, ext = os.path.splitext(relpath)
    if ext.lower() in IGNORE_EXTENSIONS:
        return True
    try:
        if os.path.getsize(abspath) > MAX_FILE_SIZE:
            return True
    except OSError:
        return True
    return False


def main() -> None:
    print(f"Connecting to database...", flush=True)
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print(f"Scanning {ROOT_DIR}...", flush=True)

    count = 0
    errors = 0

    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, ROOT_DIR)

            if should_ignore(relpath, filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                print(f"Ingesting: {relpath}", flush=True)

                # Truncate to avoid token limits
                truncated_content = content[:10000]

                # Get embedding from Gemini
                embedding = get_embedding(truncated_content)

                # Store directly in DB
                metadata = json.dumps({
                    "filename": relpath,
                    "type": "code",
                    "size": len(content),
                    "model": "text-embedding-004"
                })

                # Convert embedding list to pgvector format
                vector_str = '[' + ','.join(map(str, embedding)) + ']'

                cur.execute(
                    "INSERT INTO vector_items (content, embedding, metadata) VALUES (%s, %s, %s)",
                    (truncated_content, vector_str, metadata)
                )
                conn.commit()

                count += 1

                # Rate limit for Gemini API
                time.sleep(0.1)

            except UnicodeDecodeError:
                continue
            except Exception as e:
                errors += 1
                print(f"Error processing {relpath}: {e}", flush=True)

    cur.close()
    conn.close()

    print(f"--- Ingestion Complete. Processed {count} files. Errors: {errors} ---", flush=True)


if __name__ == "__main__":
    main()
