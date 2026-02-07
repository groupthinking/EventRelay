import subprocess
import time
from subprocess import Popen


def start_dev_server() -> Popen:
    print("🚀 Starting local dev server (apps/web)...")
    # Start the dev server in a subprocess
    process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd="/Users/garvey/Dev/projects/EventRelay/apps/web",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return process


def main() -> None:
    # In a real agentic environment, we would use the browser_subagent tool.
    # This script acts as a trigger/orchestrator for that.

    server_process = None
    try:
        server_process = start_dev_server()
        print("⏳ Waiting for server to stabilize (5s)...")
        time.sleep(5)

        print("📸 Preview ready at http://localhost:3000")
        print(
            "💡 Hint: Ask me to 'Capture a screenshot of "
            "localhost:3000' to see the current state."
        )

        # Keep the script running to maintain the server
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Stopping dev server...")
        if server_process:
            server_process.terminate()
    except Exception as e:
        print(f"❌ Error: {e}")
        if server_process:
            server_process.terminate()


if __name__ == "__main__":
    main()
