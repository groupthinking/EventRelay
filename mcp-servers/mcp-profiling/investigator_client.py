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

        target_func = "target_function"
        input_val = 30

        # --- Phase 1: Investigation ---
        print(f"\nPhase 1: Benchmarking '{target_func}' (Baseline)...")
        
        benchmark_result = await session.call_tool(
            "run_benchmark",
            arguments={"function_name": target_func, "input_value": input_val}
        )
        print(f"📊 {benchmark_result.content[0].text}")

        print(f"📉 Getting Profile Stats...")
        profile_result = await session.call_tool(
            "get_profile_stats",
            arguments={"function_name": target_func, "input_value": input_val}
        )
        # Just show the first few lines to confirm we got it
        print(f"  (Profile data received, length: {len(profile_result.content[0].text)} chars)")
        
        # --- Phase 2: Optimization (Simulated Engineer Agent) ---
        print(f"\nPhase 2: Engineer Agent is constructing a patch...")
        
        optimized_code = """
def optimized_fibonacci(n: int) -> int:
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
        print(f"🛠️ Submitting Patch for '{target_func}'...")
        
        patch_result = await session.call_tool(
            "submit_patch",
            arguments={"function_name": target_func, "python_code": optimized_code}
        )
        print(f"✨ {patch_result.content[0].text}")

        # --- Phase 3: Verification ---
        print(f"\nPhase 3: Verifying Optimization...")
        
        # Run the same benchmark again on the *same function name* which is now patched
        final_benchmark = await session.call_tool(
            "run_benchmark",
            arguments={"function_name": target_func, "input_value": input_val}
        )
        print(f"🚀 {final_benchmark.content[0].text}")


if __name__ == "__main__":
    asyncio.run(run_investigator_agent())
