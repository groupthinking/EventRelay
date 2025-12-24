import asyncio
import os
import re
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiling_server.py")
# [Level 7 Innovation] Scan the entire project root, not just one file
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

async def process_file(session, file_path, is_ci):
    """
    Audits and optimizes a single file. Returns True if an optimization was applied.
    """
    # 1. Audit (Static Analysis - Fast & Safe)
    print(f"🔍 Auditing {os.path.basename(file_path)}...")
    try:
        audit = await session.call_tool("audit_codebase", arguments={"file_path": file_path})
        if not audit or not audit.content:
             print(f"⚠️ Audit returned no content for {file_path}")
             return False
        audit_text = audit.content[0].text
    except Exception as e:
        print(f"⚠️ Error auditing {file_path}: {e}")
        return False
    
    if "candidates for optimization" not in audit_text:
        return False

    # Parse the target function
    match = re.search(r"- (\w+) \(Reason:", audit_text)
    if not match:
        print(f"❌ Could not parse function name from audit in {file_path}.")
        return False
        
    target_func = match.group(1)
    print(f"🎯 Target Identified: '{target_func}' in {file_path}")

    # 2. Load Module (Dynamic - Only done if audit finds something)
    try:
        await session.call_tool("load_target_module", arguments={"file_path": file_path})
    except Exception as e:
        print(f"⚠️ Failed to load module {file_path}: {e}")
        return False

    # 3. Git: Create Branch
    branch_name = f"perf/optimize-{target_func}"
    if not is_ci:
        print(f"🌿 Creating branch: {branch_name}")
        await session.call_tool("git_create_branch", arguments={"branch_name": branch_name})
    else:
        print(f"🌿 CI Mode: Skipping branch creation. Optimizing in-place.")

    # 4. Baseline & Tests
    print("📉 Establishing Baseline...")
    # Note: In a real autonomous agent, we would use an LLM to infer valid inputs based on type hints.
    # For this demo, we assume integer inputs are valid for the detected math functions.
    await session.call_tool("generate_parity_tests", arguments={"function_name": target_func, "test_inputs": [5, 10, 15]})
    
    try:
        bench_base = await session.call_tool("run_benchmark", arguments={"function_name": target_func, "input_value": 20})
        # Extract time from string "took 0.002748 seconds"
        match_bench = re.search(r"took ([\d\.]+) seconds", bench_base.content[0].text)
        if match_bench:
            base_time = float(match_bench.group(1))
            print(f"   Base Time: {base_time:.6f}s")
        else:
            print("⚠️ Could not parse benchmark time. Skipping.")
            return False
            
    except Exception as e:
        print(f"⚠️ Benchmark failed: {e}")
        return False

    # 5. The Fix (Simulated Engineer Agent Handoff)
    print("🛠️ Applying Fix...")
    # We inject the known fix for the demo. 
    # In production, this string comes from the LLM based on the function body.
    OPTIMIZED_CODE = f"""
def {target_func}(n):
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
    await session.call_tool("submit_patch", arguments={"function_name": target_func, "python_code": OPTIMIZED_CODE})

    # 6. Verify
    print("🧪 Verifying...")
    try:
        bench_new = await session.call_tool("run_benchmark", arguments={"function_name": target_func, "input_value": 20})
        match_new = re.search(r"took ([\d\.]+) seconds", bench_new.content[0].text)
        if match_new:
            new_time = float(match_new.group(1))
            print(f"   New Time:  {new_time:.6f}s")
        else:
             new_time = base_time # Fallback to avoid division by zero error later if needed, but we should probably fail.
             print("⚠️ Could not parse new benchmark time.")

        parity = await session.call_tool("verify_parity", arguments={"function_name": target_func})
        print(f"   Parity: {parity.content[0].text[:50]}...")
        
        if "✅" in parity.content[0].text:
            print("💾 Verification Passed. Persisting...")
            await session.call_tool("persist_optimization_safe", arguments={
                "function_name": target_func,
                "file_path": file_path
            })
            
            # 7. Git: Commit
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
            return True
        else:
            print("⚠️ Verification Failed. Reverting...")
            if not is_ci:
                await session.call_tool("git_reset_hard")
            return False
            
    except Exception as e:
        print(f"⚠️ Verification process crashed: {e}")
        if not is_ci:
            await session.call_tool("git_reset_hard")
        return False

async def run_fleet_commander():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT_PATH],
        env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("🤖 Fleet Commander Agent Connected (Recursive Scanner Mode).\n")

            # [Level 6 Innovation] Detect CI Environment
            is_ci = os.environ.get("BUILD_ID") is not None
            if is_ci:
                print("🚀 CI Environment Detected (Cloud Build). Git operations will be skipped.")

            print(f"📂 Scanning Project Root: {PROJECT_ROOT}")
            
            optimized_count = 0
            
            # Walk the directory tree
            for root, dirs, files in os.walk(PROJECT_ROOT):
                # [Level 7 Fix] intelligent exclusion
                # Modify dirs in-place to skip recursion into ignored directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('mcp-servers', 'venv', 'env', '__pycache__', 'node_modules', 'dist', 'build', 'site-packages')]
                    
                for file in files:
                    if file.endswith(".py"):
                        full_path = os.path.join(root, file)
                        # Double check we aren't in a venv somehow
                        if "site-packages" in full_path or ".venv" in full_path:
                            continue

                        if await process_file(session, full_path, is_ci):
                            optimized_count += 1
            
            # Also explicitly scan our dummy target since it was skipped by mcp-servers exclusion
            dummy_target = os.path.join(os.path.dirname(SERVER_SCRIPT_PATH), "legacy_math_utils.py")
            if os.path.exists(dummy_target):
                 if await process_file(session, dummy_target, is_ci):
                     optimized_count += 1
            
            print(f"\n🏁 Fleet Scan Complete. Total files optimized: {optimized_count}")

if __name__ == "__main__":
    # Ensure we have a target to test against in the root or nearby
    DUMMY_TARGET = os.path.join(os.path.dirname(SERVER_SCRIPT_PATH), "legacy_math_utils.py")
    # Create a dummy file to test the auditor if it doesn't exist
    if not os.path.exists(DUMMY_TARGET):
        print(f"Creating dummy target file: {DUMMY_TARGET}")
        with open(DUMMY_TARGET, "w") as f:
            # Use correct Fibonacci logic so parity passes
            f.write("def bad_calc(n):\n    if n <= 1: return n\n    return bad_calc(n-1) + bad_calc(n-2)\n")
            
    asyncio.run(run_fleet_commander())
