import os
import json
import sys
import subprocess
from openai import OpenAI

# Configuration
MCP_SERVER_EXECUTABLE = "/usr/local/bin/node"
MCP_SERVER_SCRIPT = os.path.abspath("mcp-servers/gcp-vector-db/build/index.js")
# Ensure OPENAI_API_KEY is retrieved from env
API_KEY = os.environ.get("OPENAI_API_KEY")

if not API_KEY:
    print("Error: OPENAI_API_KEY environment variable not set.")
    sys.exit(1)

client = OpenAI(api_key=API_KEY)

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
        init_req = self.rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "chatter", "version": "1.0"}})
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
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model="text-embedding-3-small").data[0].embedding

def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_docs.py \"Your question here\"")
        return # Exit gracefully to not error out the workflow if args missing

    query = sys.argv[1]
    print(f"\n🔍 Searching docs for: '{query}'...\n")

    try:
        mcp = MCPClient()
    except Exception as e:
        print(f"Failed to start MCP server: {e}")
        return

    # 1. Embed Query
    query_vector = get_embedding(query)

    # 2. Search
    res = mcp.call_tool("search_similar", {
        "vector": query_vector,
        "limit": 3,
        "threshold": 0.3 # Somewhat loose threshold for demo
    })

    mcp.close()

    try:
        content_block = res.get('content', [{}])[0]
        text_content = content_block.get('text', '[]')
        results = json.loads(text_content)
    except:
        print(f"Error parsing results: {res}")
        return

    if not results:
        print("No relevant documentation found.")
        return

    print("--- 📄 Relevant Documentation ---")
    context = ""
    for idx, item in enumerate(results):
        meta = item.get('metadata', {})
        filename = meta.get('filename', 'Unknown File')
        print(f"\n[{idx+1}] {filename} (Similarity: {item.get('similarity', 0):.4f})")
        # Print snippet
        snippet = item.get('content', '')[:300].replace("\n", " ")
        print(f"    \"{snippet}...\"")

        context += f"Source: {filename}\nContent: {item.get('content')}\n\n"

    # 3. Final Answer (Using LLM)
    print("\n--- 🤖 AI Answer ---")
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo", # Cost effective for demo
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Answer the user's question using ONLY the provided context. If the answer is not in the context, say so."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ]
    )
    print(completion.choices[0].message.content)
    print("\n--------------------")

if __name__ == "__main__":
    main()
