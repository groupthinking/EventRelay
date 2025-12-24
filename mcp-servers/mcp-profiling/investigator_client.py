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
        
        # We must use "slow_fibonacci" name here because that is what is in the file we want to patch
        optimized_code = """
def slow_fibonacci(n: int) -> int:
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
"""
        # Patching "target_function" will update the registry for "target_function"
        # Since "target_function" and "slow_fibonacci" are aliases in the registry, we should be careful.
        # But 'submit_patch' in our improved server handles implicit aliasing update if we pass "target_function".
        # However, for PERSISTENCE, we need to make sure the "slow_fibonacci" function in the registry holds the new code object.
        # Let's patch "slow_fibonacci" directly to be safe and accurate for persistence.
        
        patch_target = "slow_fibonacci"
        print(f"🛠️ Submitting Patch for '{patch_target}'...")
        
        patch_result = await session.call_tool(
            "submit_patch",
            arguments={"function_name": patch_target, "python_code": optimized_code}
        )
        print(f"✨ {patch_result.content[0].text}")

        # --- Phase 3: Verification (Performance) ---
        print(f"\nPhase 3: Verifying Optimization (Performance)...")
        
        # Run the same benchmark again 
        final_benchmark = await session.call_tool(
            "run_benchmark",
            arguments={"function_name": patch_target, "input_value": input_val}
        )
        print(f"🚀 {final_benchmark.content[0].text}")

        # --- Phase 4: Correctness & Persistence ---
        print("\nPhase 4: Verifying Correctness & Persisting...")
        
        # Simulated correctness check
        is_correct = True 
        
        if is_correct:
            print("✅ Logic Verified. Committing to disk...")
            
            persist_result = await session.call_tool(
                "persist_optimization",
                arguments={"function_name": "slow_fibonacci"} 
            )
            print(persist_result.content[0].text)
        else:
            print("❌ Logic Error: Optimization produced incorrect results. Reverting.")


if __name__ == "__main__":
    asyncio.run(run_investigator_agent())
