import json
import os
import subprocess
import sys
from typing import Optional, Any, Dict, List, Union

# Configuration
MCP_SERVER_EXECUTABLE = "/usr/local/bin/node"
MCP_SERVER_SCRIPT = os.path.abspath("mcp-servers/gcp-vector-db/build/index.js")

class MCPClient:
    def __init__(self) -> None:
        env = os.environ.copy()
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
        init_req = self.rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "debugger", "version": "1.0"}})
        self.process.stdin.write(init_req + "\n")
        self.process.stdin.flush()
        self.process.stdout.readline()
        self.process.stdin.write(self.rpc_request("notifications/initialized") + "\n")
        self.process.stdin.flush()
        self.process.stdin.write(self.rpc_request("tools/list") + "\n")
        self.process.stdin.flush()
        self.process.stdout.readline()

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Union[Dict[str, Any], str]:
        req = self.rpc_request("tools/call", {"name": tool_name, "arguments": arguments})
        self.process.stdin.write(req + "\n")
        self.process.stdin.flush()
        response_line = self.process.stdout.readline()
        return json.loads(response_line)

    def close(self) -> None:
        self.process.terminate()

def main() -> None:
    mcp = MCPClient()

    # Check count
    print("Checking row count...")
    res = mcp.call_tool("execute_sql", {"sql": "SELECT COUNT(*) FROM vector_items"})
    print(f"Result: {res}")

    # Check a sample
    print("\nChecking sample item...")
    res = mcp.call_tool("execute_sql", {"sql": "SELECT metadata FROM vector_items LIMIT 1"})
    print(f"Sample: {res}")

    mcp.close()

if __name__ == "__main__":
    main()
