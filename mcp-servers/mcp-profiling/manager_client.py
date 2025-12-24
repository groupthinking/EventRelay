import asyncio
import os
import re
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiling_server.py")
TARGET_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy_math_utils.py")

async def run_contributor_agent():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT_PATH],
        env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("🤖 Autonomous Contributor Agent Connected.\n")

            # [Level 6 Innovation] Detect CI Environment
            is_ci = os.environ.get("BUILD_ID") is not None
            if is_ci:
                print("🚀 CI Environment Detected (Cloud Build). Git operations will be skipped.")

            # 1. Audit
            print(f"🔍 Auditing {TARGET_FILE}...")
            await session.call_tool("load_target_module", arguments={"file_path": TARGET_FILE})
            audit = await session.call_tool("audit_codebase", arguments={"file_path": TARGET_FILE})
            audit_text = audit.content[0].text
            
            if "candidates for optimization" not in audit_text:
                print("✅ No optimizations needed.")
                return

            # Parse the target function (Simple regex for demo)
            match = re.search(r"- (\w+) \(Reason:", audit_text)
            if not match:
                print("❌ Could not parse function name from audit.")
                return
                
            target_func = match.group(1)
            print(f"🎯 Target Identified: '{target_func}'")

            # 2. Git: Create Branch
            if not is_ci:
                branch_name = f"perf/optimize-{target_func}"
                print(f"🌿 Creating branch: {branch_name}")
                await session.call_tool("git_create_branch", arguments={"branch_name": branch_name})
            else:
                branch_name = "in-place-optimization" # Placeholder for logging
                print(f"🌿 CI Mode: Skipping branch creation. Optimizing in-place.")

            # 3. Baseline & Tests
            print("📉 Establishing Baseline...")
            await session.call_tool("generate_parity_tests", arguments={"function_name": target_func, "test_inputs": [5, 10, 15]})
            
            bench_base = await session.call_tool("run_benchmark", arguments={"function_name": target_func, "input_value": 20})
            # Extract time from string "took 0.002748 seconds"
            base_time = float(re.search(r"took ([\d\.]+) seconds", bench_base.content[0].text).group(1))
            print(f"   Base Time: {base_time:.6f}s")

            # 4. The Fix (Simulated Engineer Agent Handoff)
            print("🛠️ Applying Fix...")
            # We inject the known fix for the demo
            OPTIMIZED_CODE = f"""
def {target_func}(n):
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
            await session.call_tool("submit_patch", arguments={"function_name": target_func, "python_code": OPTIMIZED_CODE})

            # 5. Verify
            print("🧪 Verifying...")
            bench_new = await session.call_tool("run_benchmark", arguments={"function_name": target_func, "input_value": 20})
            new_time = float(re.search(r"took ([\d\.]+) seconds", bench_new.content[0].text).group(1))
            print(f"   New Time:  {new_time:.6f}s")

            parity = await session.call_tool("verify_parity", arguments={"function_name": target_func})
            print(f"   Parity: {parity.content[0].text[:50]}...") # Print first part of result
            
            if "✅" in parity.content[0].text:
                print("💾 Verification Passed. Persisting...")
                await session.call_tool("persist_optimization_safe", arguments={"function_name": target_func})
                
                # 6. Git: Commit (Conditional)
                if not is_ci:
                    print("📝 Committing to Git...")
                    commit = await session.call_tool(
                        "git_commit_optimization", 
                        arguments={
                            "function_name": target_func,
                            "baseline_time": base_time,
                            "optimized_time": new_time
                        }
                    )
                    print(f"\n{commit.content[0].text}")
                    print(f"\n🚀 Ready to Push! Branch '{branch_name}' contains the fix.")
                else:
                    print("📝 CI Mode: Skipping Git Commit. Optimization applied to build artifact.")
            else:
                print("⚠️ Verification Failed. Reverting...")
                if not is_ci:
                    await session.call_tool("git_reset_hard")
                else:
                    print("⚠️ CI Mode: Reverting isn't strictly necessary as build will fail, but good practice.")
                    # In CI, we might not have git reset capabilities if it's a shallow clone without the commit history, 
                    # or if we are just modifying files. For now, we'll skip reset or implement a file restore if needed.
                    # Since persist_optimization_safe creates a backup, we could use restore_backup tool if fully integrated.
                    await session.call_tool("restore_backup") # Using the restore tool we added earlier!

if __name__ == "__main__":
    # Create a dummy file to test the auditor if it doesn't exist
    if not os.path.exists(TARGET_FILE):
        print(f"Creating dummy target file: {TARGET_FILE}")
        with open(TARGET_FILE, "w") as f:
            # Use correct Fibonacci logic so parity passes
            f.write("def bad_calc(n):\n    if n <= 1: return n\n    return bad_calc(n-1) + bad_calc(n-2)\n")
            
    asyncio.run(run_contributor_agent())
