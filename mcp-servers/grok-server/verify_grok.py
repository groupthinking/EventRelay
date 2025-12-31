import subprocess
import json
import os
import sys

def run_verification():
    print("Starting grok-server verification...")
    
    env = os.environ.copy()
    env["GROK_EMAIL"] = "test@example.com"
    env["GROK_PASSWORD"] = "password123"
    
    process = subprocess.Popen(
        ["node", "build/index.js"],
        cwd="/Users/garvey/Dev/projects/EventRelay/mcp-servers/grok-server",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr, # print logs to stderr
        env=env,
        text=True,
        bufsize=0
    )

    try:
        # 1. Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        
        print("Sending initialize...")
        process.stdin.write(json.dumps(init_req) + "\n")
        process.stdin.flush()
        
        # Read init response
        response_line = process.stdout.readline()
        if not response_line:
            print("Error: No response from server during initialize")
            return False
            
        print(f"Init response: {response_line.strip()}")
        init_res = json.loads(response_line)
        if "error" in init_res:
            print(f"Server returned error: {init_res['error']}")
            return False

        # 2. Initialized notification
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        process.stdin.write(json.dumps(notif) + "\n")
        process.stdin.flush()

        # 3. List Tools
        list_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        print("Sending tools/list...")
        process.stdin.write(json.dumps(list_req) + "\n")
        process.stdin.flush()
        
        response_line = process.stdout.readline()
        if not response_line:
             print("Error: No response from server during tools/list")
             return False
             
        print(f"Tools response: {response_line.strip()}")
        tools_res = json.loads(response_line)
        
        if "result" in tools_res and "tools" in tools_res["result"]:
            tools = tools_res["result"]["tools"]
            tool_names = [t["name"] for t in tools]
            print(f"Found tools: {tool_names}")
            
            expected_tools = ["execute_code", "web_interaction"]
            if all(t in tool_names for t in expected_tools):
                print("SUCCESS: All expected tools found.")
                return True
            else:
                print(f"FAILURE: Missing tools. Expected {expected_tools}, found {tool_names}")
                return False
        else:
            print("FAILURE: Invalid tools response structure")
            return False

    except Exception as e:
        print(f"Exception during verification: {e}")
        return False
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()

if __name__ == "__main__":
    if run_verification():
        sys.exit(0)
    else:
        sys.exit(1)
