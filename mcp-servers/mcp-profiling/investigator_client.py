import asyncio
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# --- Configuration ---
# Point this to the server file we created in the previous step
SERVER_SCRIPT_PATH = "./profiling_server.py"

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

        # 3. Discovery: The Agent asks "What can I do here?"
        tools_response = await session.list_tools()
        available_tools = {tool.name: tool for tool in tools_response.tools}
        
        print(f"🔍 Discovered Tools: {list(available_tools.keys())}")

        # --- A2A Simulation Start ---
        # In a real scenario, an LLM would decide these steps based on the 'available_tools' list.
        # Here, we simulate the 'Investigator' deciding to profile a suspicious function.

        target_func = "slow_fibonacci"
        input_val = 30

        print(f"\n🤖 Agent Decision: Benchmarking '{target_func}'...")
        
        # 4. Execution: Call the 'run_benchmark' tool via MCP
        benchmark_result = await session.call_tool(
            "run_benchmark",
            arguments={"function_name": target_func, "input_value": input_val}
        )
        
        print(f"📊 {benchmark_result.content[0].text}")

        print(f"\n🤖 Agent Decision: Deep profiling required for '{target_func}'...")

        # 5. Deep Dive: Call the 'get_profile_stats' tool
        profile_result = await session.call_tool(
            "get_profile_stats",
            arguments={"function_name": target_func, "input_value": input_val}
        )

        print("📉 Profiler Output (Top Bottlenecks):")
        print(profile_result.content[0].text)
        
        # --- A2A Simulation End ---
        
        # The 'Investigator' would now pass this text output to the 'Engineer' Agent
        # to generate the optimized code.

if __name__ == "__main__":
    asyncio.run(run_investigator_agent())
