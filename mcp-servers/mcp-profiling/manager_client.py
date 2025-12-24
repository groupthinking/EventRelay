import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiling_server.py")
TARGET_FILE_TO_OPTIMIZE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "legacy_math_utils.py")

async def run_manager_agent():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT_PATH],
        env=os.environ.copy()
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("🕵️ Manager Agent Connected.")

            # Phase 1: Ingestion
            print(f"\n📂 Loading Target Module: {TARGET_FILE_TO_OPTIMIZE}...")
            load_result = await session.call_tool(
                "load_target_module",
                arguments={"file_path": TARGET_FILE_TO_OPTIMIZE}
            )
            print(load_result.content[0].text)

            # Phase 2: The Audit (Static Analysis)
            print("\n🔍 Running Static Analysis Audit...")
            audit_result = await session.call_tool(
                "audit_codebase",
                arguments={"file_path": TARGET_FILE_TO_OPTIMIZE}
            )
            audit_text = audit_result.content[0].text
            print(audit_text)

            # Phase 3: Autonomous Delegation
            # In a real LLM loop, the model would parse the 'audit_text' to extract function names.
            # Here, we simulate the Agent picking the first flagged function.
            
            if "candidates for optimization" in audit_text:
                # Simple parsing simulation
                target_line = audit_text.split("\n- ")[1] # Get first candidate
                target_func = target_line.split(" ")[0]   # Extract name
                reason = target_line.split("Reason: ")[1].strip(")")
                
                print(f"\n🤖 DECISION: Targeting '{target_func}' due to {reason}.")
                
                # Trigger the existing TDD Workflow (Simulated Handoff)
                # 1. Generate Tests
                print(f"   -> Generating Parity Tests for {target_func}...")
                await session.call_tool("generate_parity_tests", arguments={"function_name": target_func, "test_inputs": [5, 10, 15]})
                
                # 2. Benchmark
                print(f"   -> Benchmarking {target_func}...")
                bench = await session.call_tool("run_benchmark", arguments={"function_name": target_func, "input_value": 20})
                print(f"      {bench.content[0].text}")
                
            else:
                print("✅ Codebase looks clean. No actions required.")

if __name__ == "__main__":
    # Create a dummy file to test the auditor if it doesn't exist
    if not os.path.exists(TARGET_FILE_TO_OPTIMIZE):
        print(f"Creating dummy target file: {TARGET_FILE_TO_OPTIMIZE}")
        with open(TARGET_FILE_TO_OPTIMIZE, "w") as f:
            f.write("def bad_calc(n):\n    if n<1: return n\n    return bad_calc(n-1) + bad_calc(n-2)\n")
            
    asyncio.run(run_manager_agent())
