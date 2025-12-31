import subprocess
import json
import os
import sys
import time

def run_verification():
    print("Starting grok-server verification (Headless: False)...")
    
    env = os.environ.copy()
    env["GROK_EMAIL"] = "test@example.com"
    env["GROK_PASSWORD"] = "password123"
    env["HEADLESS"] = "false" # Force visible browser
    
    process = subprocess.Popen(
        ["node", "build/index.js"],
        cwd="/Users/garvey/Dev/projects/EventRelay/mcp-servers/grok-server",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
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
        
        response_line = process.stdout.readline()
        if not response_line:
            return False
            
        print(f"Init response: {response_line.strip()}")
        init_res = json.loads(response_line) # Consume init response
        
        # 2. Initialized
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()

        # 3. Call Tool to Trigger Browser Launch
        # We call execute_code which calls getSession() which launches puppeteer
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "execute_code",
                "arguments": {
                    "code": "print('hello')",
                    "language": "python"
                }
            }
        }
        
        print("Sending tools/call to trigger browser launch...")
        process.stdin.write(json.dumps(call_req) + "\n")
        process.stdin.flush()
        
        if sys.stdin.isatty():
            input("Press Enter to stop the server and close the browser...")
        else:
            print("Non-interactive mode detected. Waiting 30 seconds...")
            time.sleep(30)
        
        # We don't necessarily expect a success response because login will fail with dummy creds
        # But we want to keep the process alive long enough to see.
        
        # Attempt to read response (might be error due to login fail)
        # But since we are mocking, we just want to see the window.
        
    except Exception as e:
        print(f"Exception: {e}")
    finally:
        print("Closing server...")
        try:
            # Send shutdown
            # process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "shutdown"}) + "\n")
            # process.stdin.flush()
            pass
        except:
            pass
            
        process.terminate()
        process.wait()

if __name__ == "__main__":
    run_verification()
