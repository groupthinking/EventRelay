import asyncio
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- Configuration ---
# Point this to the server file we created in the previous step
SERVER_SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiling_server.py")

async def run_investigator_agent():
    """
    This function acts as the 'Investigator Agent'. 
    It connects to the MCP server, discovers tools, and executes a profiling workflow.
    """
    
    # Define how to launch the server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_SCRIPT_PATH],
        env=os.environ.copy() # Pass environment vars if needed
    )

    async with AsyncExitStack() as stack:
        # 1. Transport Layer: Start the server process and connect via stdio
        read, write = await stack.enter_async_context(stdio_client(server_params))
        
        # 2. Protocol Layer: Initialize the MCP session
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        
        print("✅ Connected to PerformanceOptimizer Server")

        # 3. Discovery
        tools_response = await session.list_tools()
        available_tools = {tool.name: tool for tool in tools_response.tools}
        
        print(f"🔍 Discovered Tools: {list(available_tools.keys())}")

        target_func = "slow_fibonacci"
        input_val = 30

        # --- Phase 1: Establish Baseline & Generate Tests ---
        print(f"\n📉 Running Baseline & Generating Tests for '{target_func}'...")
        
        # We pick a range of inputs: small (edge cases) and medium
        test_inputs = [0, 1, 2, 5, 10, 15] 
        
        test_result = await session.call_tool(
            "generate_parity_tests",
            arguments={"function_name": target_func, "test_inputs": test_inputs}
        )
        print(test_result.content[0].text)
        
        # Run benchmark to get baseline speed
        benchmark_baseline = await session.call_tool(
            "run_benchmark",
            arguments={"function_name": target_func, "input_value": input_val}
        )
        print(f"📊 Baseline Speed: {benchmark_baseline.content[0].text}")


        # --- Phase 2: Apply Optimization Patch ---
        print(f"\n🚀 Applying Optimization Patch...")
        
        optimized_code = """
def slow_fibonacci(n: int) -> int:
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
        patch_result = await session.call_tool(
            "submit_patch",
            arguments={"function_name": target_func, "python_code": optimized_code}
        )
        print(f"✨ {patch_result.content[0].text}")

        # --- Phase 3: Verify Performance ---
        print(f"\n📈 Verifying Performance...")
        benchmark_new = await session.call_tool(
            "run_benchmark",
            arguments={"function_name": target_func, "input_value": input_val}
        )
        print(f"🚀 Optimized Speed: {benchmark_new.content[0].text}")

        # --- Phase 4: Verify Correctness (TDD) ---
        print("\n🧪 Verifying Logic Parity...")
        parity_result = await session.call_tool(
            "verify_parity",
            arguments={"function_name": target_func}
        )
        print(parity_result.content[0].text)

        # --- Phase 5: Conditional Persist ---
        if "✅" in parity_result.content[0].text:
            print("\n💾 Tests Passed. Persisting to disk (with backup)...")
            persist_result = await session.call_tool(
                "persist_optimization_safe", # Use the new safe tool
                arguments={"function_name": target_func}
            )
            print(persist_result.content[0].text)
        else:
            print("\n⚠️ Tests Failed! Discarding patch.")
            # Ideally, we would call a 'rollback' tool here if implemented


if __name__ == "__main__":
    asyncio.run(run_investigator_agent())
