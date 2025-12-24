import time
import cProfile
import pstats
import io
import functools
from typing import Any, Callable, Dict
from mcp.server.fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("PerformanceOptimizer")

# --- The Codebase (Simulation) ---
# In a real scenario, this would be imported from your project files.

def slow_fibonacci(n: int) -> int:
    """Inefficient recursive implementation."""
    if n <= 1:
        return n
    return slow_fibonacci(n-1) + slow_fibonacci(n-2)

def optimized_fibonacci(n: int) -> int:
    """Optimized iterative implementation."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Registry of functions available for the agent to test
FUNCTION_REGISTRY = {
    "slow_fibonacci": slow_fibonacci,
    "optimized_fibonacci": optimized_fibonacci
}

# --- MCP Tools ---

@mcp.tool()
def run_benchmark(function_name: str, input_value: int, iterations: int = 1) -> str:
    """
    Runs a benchmark on a registered function and returns execution time.
    Use this to establish a baseline before optimization.
    """
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: Function '{function_name}' not found in registry."
    
    func = FUNCTION_REGISTRY[function_name]
    
    start_time = time.perf_counter()
    for _ in range(iterations):
        func(input_value)
    end_time = time.perf_counter()
    
    avg_time = (end_time - start_time) / iterations
    return f"Benchmark Result: {function_name}({input_value}) took {avg_time:.6f} seconds (avg over {iterations} runs)."

@mcp.tool()
def get_profile_stats(function_name: str, input_value: int) -> str:
    """
    Runs cProfile on the function to identify internal bottlenecks.
    Returns the top 10 lines by cumulative time.
    """
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: Function '{function_name}' not found."

    func = FUNCTION_REGISTRY[function_name]
    
    profiler = cProfile.Profile()
    profiler.enable()
    func(input_value)
    profiler.disable()
    
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats(10)
    
    return s.getvalue()

if __name__ == "__main__":
    # This starts the MCP server, allowing Gemini/Agents to connect to it.
    mcp.run()
