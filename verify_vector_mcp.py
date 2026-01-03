import json
import os
import subprocess
import sys

# Configuration
SERVER_PATH = os.path.join(os.getcwd(), "mcp-servers/gcp-vector-db/build/index.js")
NODE_PATH = "/usr/local/bin/node"

def rpc_request(method, params=None, req_id=1):
    msg = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method
    }
    if params:
        msg["params"] = params
    return json.dumps(msg)

def run_verification():
    print(f"Starting server: {NODE_PATH} {SERVER_PATH}")

    # We need to set DATABASE_URL (Mock it or fail gracefully if not set)
    # Since we can't easily access the prod DB here without auth, we might expect failure or need a mock.
    # For now, let's just see if it lists tools.
    env = os.environ.copy()
    env["DATABASE_URL"] = "postgresql://user:password@localhost:5432/mockdb"

    process = subprocess.Popen(
        [NODE_PATH, SERVER_PATH],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=0
    )

    try:
        # 1. Initialize
        init_req = rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "verifier", "version": "1.0"}}, req_id=0)
        print(f"Sending: {init_req}")
        process.stdin.write(init_req + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        print(f"Received: {response.strip()}")

        # 2. List Tools
        tools_req = rpc_request("tools/list", req_id=1)
        print(f"Sending: {tools_req}")
        process.stdin.write(tools_req + "\n")
        process.stdin.flush()

        response = process.stdout.readline()
        print(f"Received: {response.strip()}")

        if "init_vector_extension" in response and "store_item" in response:
             print("\n[SUCCESS] Tools listed correctly!")
        else:
             print("\n[FAIL] Expected tools not found.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        process.terminate()
        stderr = process.stderr.read()
        if stderr:
            print(f"Server Stderr: {stderr}")

if __name__ == "__main__":
    run_verification()
