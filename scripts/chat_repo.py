import os
import json
import sys
import subprocess
import google.generativeai as genai

# Configuration
MCP_SERVER_EXECUTABLE = "/usr/local/bin/node"
MCP_SERVER_SCRIPT = os.path.abspath("mcp-servers/gcp-vector-db/build/index.js")
# Using one of the keys provided
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyAy4ywrl9sP4E-S0I07rAixgrVg1xKjFIM")
genai.configure(api_key=GOOGLE_API_KEY)

EMBEDDING_MODEL = "models/text-embedding-004"
CHAT_MODEL = "gemini-2.0-flash-exp" # Or gemini-1.5-pro

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
        init_req = self.rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "repo-chatter", "version": "1.0"}})
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
        task_type="retrieval_query"
    )
    return result['embedding']

def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_repo.py \"Your question here\"")
        return

    query = sys.argv[1]
    print(f"\n🔍 Searching repository for: '{query}'...\n")

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
        "limit": 5,
        "threshold": 0.35 # Slightly stricter for code
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
        print("No relevant code found.")
        return

    print("--- 📄 Relevant Files ---")
    context = ""
    for idx, item in enumerate(results):
        meta = item.get('metadata', {})
        filename = meta.get('filename', 'Unknown File')
        print(f"\n[{idx+1}] {filename} (Similarity: {item.get('similarity', 0):.4f})")

        snippet = item.get('content', '')[:100].replace("\n", " ")
        print(f"    \"{snippet}...\"")

        context += f"Source: {filename}\nContent:\n```\n{item.get('content')}\n```\n\n"

    # 3. Final Answer (Using Gemini)
    print("\n--- 🤖 Gemini 2.0 Answer ---")
    model = genai.GenerativeModel(CHAT_MODEL)

    prompt = f"""You are a helpful expert software engineer. Answer the user's question about the codebase using ONLY the provided file contexts. Explain your reasoning. If the answer is not in the context, say so.

Context:
{context}

Question: {query}
"""
    response = model.generate_content(prompt)
    print(response.text)
    print("\n--------------------")

if __name__ == "__main__":
    main()
