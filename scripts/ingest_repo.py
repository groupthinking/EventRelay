import os
import json
import subprocess
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

print("DEBUG: Imports done", flush=True)

# Google Gemini Configuration
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    print(f"DEBUG: Using GOOGLE_API_KEY starting with {GOOGLE_API_KEY[:10]}...", flush=True)
else:
    print("DEBUG: GOOGLE_API_KEY is missing", flush=True)

# Configuration
MCP_SERVER_EXECUTABLE = "/usr/local/bin/node"
MCP_SERVER_SCRIPT = os.path.abspath("mcp-servers/gcp-vector-db/build/index.js")
ROOT_DIR = os.getcwd()

# Google Gemini Configuration
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in environment.")
    exit(1)

genai.configure(api_key=GOOGLE_API_KEY)
# Use the latest embedding model
EMBEDDING_MODEL = "models/text-embedding-004"

# Filters
IGNORE_DIRS = {
    '.git', '__pycache__', 'node_modules', 'dist', 'build', '.venv',
    'venv', 'coverage', '.idea', '.vscode', 'tmp', 'logs',
    'mcp-servers/gcp-vector-db/build', 'Gemini_Brain', '.gemini',
    '.venv_prod_verify', 'ai-edge-torch', 'video_representations_extractor-1.14.0',
    '.mypy_cache', '.ruff_cache', '.pytest_cache'
}
IGNORE_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib', '.class', '.jar',
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.mp4', '.avi',
    '.mov', '.mp3', '.wav', '.zip', '.tar', '.gz', '.7z', '.pdf',
    '.exe', '.bin', '.lock', 'package-lock.json', 'yarn.lock', '.rtf'
}
MAX_FILE_SIZE = 100 * 1024

class MCPClient:
    def __init__(self):
        env = os.environ.copy()
        if "DATABASE_URL" not in env:
             pass

        self.process = subprocess.Popen(
            [MCP_SERVER_EXECUTABLE, MCP_SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            text=True,
            bufsize=0
        )
        self.req_id = 0
        self.initialize()

    def rpc_request(self, method, params=None):
        self.req_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": method
        }
        if params:
            msg["params"] = params
        return json.dumps(msg)

    def initialize(self):
        init_req = self.rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "repo-ingester", "version": "1.0"}})
        self.process.stdin.write(init_req + "\n")
        self.process.stdin.flush()
        self.process.stdout.readline()

        self.process.stdin.write(self.rpc_request("notifications/initialized") + "\n")
        self.process.stdin.flush()

        self.process.stdin.write(self.rpc_request("tools/list") + "\n")
        self.process.stdin.flush()
        self.process.stdout.readline()

    def call_tool(self, tool_name, arguments):
        req = self.rpc_request("tools/call", {"name": tool_name, "arguments": arguments})
        self.process.stdin.write(req + "\n")
        self.process.stdin.flush()

        response_line = self.process.stdout.readline()
        try:
            response = json.loads(response_line)
            if "error" in response:
                return f"Error: {response['error']}"
            return response.get("result", {})
        except json.JSONDecodeError:
            return f"Error decoding: {response_line}"

    def close(self):
        self.process.terminate()

def get_embedding(text):
    result = genai.embed_content(
        model=EMBEDDING_MODEL,
        content=text,
        task_type="retrieval_document",
        title="Code Snippet"
    )
    return result['embedding']

def should_ignore(path):
    parts = path.split(os.sep)
    for part in parts:
        if part in IGNORE_DIRS:
            return True

    _, ext = os.path.splitext(path)
    if ext.lower() in IGNORE_EXTENSIONS:
        return True

    try:
        if os.path.getsize(path) > MAX_FILE_SIZE:
             return True
    except OSError:
        return True

    return False

def main():
    print("--- Starting Repository Ingestion (Gemini Embeddings) ---")

    try:
        mcp = MCPClient()
    except Exception as e:
        print(f"Failed to start MCP server: {e}")
        return

    print("Initializing Database (pgvector)...")
    mcp.call_tool("init_vector_extension", {})

    print(f"Scanning {ROOT_DIR}...")

    count = 0
    for root, dirs, files in os.walk(ROOT_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            filepath = os.path.join(root, file)
            relpath = os.path.relpath(filepath, ROOT_DIR)

            if should_ignore(filepath):
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip():
                    continue

                print(f"Ingesting: {relpath}")

                # Truncate to avoid Gemini token limits (approx 10k chars is safe)
                truncated_content = content[:10000]

                embedding = get_embedding(truncated_content)

                res = mcp.call_tool("store_item", {
                    "content": truncated_content,
                    "vector": embedding,
                    "metadata": json.dumps({
                        "filename": relpath,
                        "type": "code",
                        "size": len(content),
                        "model": "text-embedding-004"
                    })
                })
                count += 1

            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"Error processing {relpath}: {e}")

    mcp.close()
    print(f"--- Ingestion Complete. Processed {count} files. ---")

if __name__ == "__main__":
    main()
