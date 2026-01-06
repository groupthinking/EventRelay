import os
import json
import sys
import subprocess
import glob
from typing import Optional, Any, Dict, List, Union
from openai import OpenAI

# Configuration
MCP_SERVER_EXECUTABLE = "/usr/local/bin/node"
MCP_SERVER_SCRIPT = os.path.abspath("mcp-servers/gcp-vector-db/build/index.js")
DOCS_DIR = os.path.abspath("shared")
# Ensure OPENAI_API_KEY is retrieved from env
API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)

client = OpenAI(api_key=API_KEY)

class MCPClient:
    def __init__(self) -> None:
        env = os.environ.copy()
        # Mock connection for now if not set, but user likely has it or we can prompt
        # We assume the user runs this script with the correct env var DATABASE_URL set
        if "DATABASE_URL" not in env:
             # Default to local for dev if not provided (safety fallback)
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

    def rpc_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> str:
        self.req_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": method
        }
        if params:
            msg["params"] = params
        return json.dumps(msg)

    def initialize(self) -> None:
        # MCP Handshake
        init_req = self.rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "ingester", "version": "1.0"}})
        self.process.stdin.write(init_req + "\n")
        self.process.stdin.flush()
        self.process.stdout.readline() # Read response

        # Initialized notification
        self.process.stdin.write(self.rpc_request("notifications/initialized") + "\n")
        self.process.stdin.flush()

        # List tools to ensure ready
        self.process.stdin.write(self.rpc_request("tools/list") + "\n")
        self.process.stdin.flush()
        self.process.stdout.readline()

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Union[Dict[str, Any], str]:
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

    def close(self) -> None:
        self.process.terminate()

def get_embedding(text: str) -> List[float]:
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def main() -> None:
    print("--- Starting Documentation Ingestion ---")

    # 1. Connect to MCP
    print(f"Connecting to MCP Server: {MCP_SERVER_SCRIPT}...")
    try:
        mcp = MCPClient()
    except Exception as e:
        print(f"Failed to start MCP server: {e}")
        return

    # 2. Init DB Extension
    print("Initializing Database (pgvector)...")
    res = mcp.call_tool("init_vector_extension", {})
    print(f"Init Result: {res}")

    # 3. Read and Ingest Files
    files = glob.glob(os.path.join(DOCS_DIR, "*"))
    print(f"Found {len(files)} files in {DOCS_DIR}")

    for filepath in files:
        if not os.path.isfile(filepath): continue
        filename = os.path.basename(filepath)

        print(f"Processing {filename}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple chunking if needed, but for docs we might just do whole file for now
            # or first 5000 chars to fit context window/embedding limit.
            # Truncate to reasonable size for demo.
            truncated_content = content[:8000]

            embedding = get_embedding(truncated_content)

            res = mcp.call_tool("store_item", {
                "content": truncated_content,
                "vector": embedding,
                "metadata": json.dumps({"filename": filename, "type": "documentation"})
            })

            if "isError" in str(res):
                print(f"❌ Failed to store {filename}: {res}")
            else:
                print(f"✅ Stored {filename}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    mcp.close()
    print("--- Ingestion Complete ---")

if __name__ == "__main__":
    main()
