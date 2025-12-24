import time
import cProfile
import pstats
import io
import types
from mcp.server.fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("PerformanceOptimizer")

# --- The Codebase (Dynamic Registry) ---
# We use a mutable dictionary so we can swap implementations at runtime.

def slow_fibonacci(n: int) -> int:
    if n <= 1: return n
    return slow_fibonacci(n-1) + slow_fibonacci(n-2)

FUNCTION_REGISTRY = {
    "target_function": slow_fibonacci # We alias the function we are working on
}

# --- MCP Tools ---

@mcp.tool()
def run_benchmark(function_name: str, input_value: int, iterations: int = 1) -> str:
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: Function '{function_name}' not found."
    
    func = FUNCTION_REGISTRY[function_name]
    
    start_time = time.perf_counter()
    for _ in range(iterations):
        func(input_value)
    end_time = time.perf_counter()
    
    avg_time = (end_time - start_time) / iterations
    return f"Benchmark Result: {function_name}({input_value}) took {avg_time:.6f} seconds."

@mcp.tool()
def get_profile_stats(function_name: str, input_value: int) -> str:
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

@mcp.tool()
def submit_patch(function_name: str, python_code: str) -> str:
    """
    INNOVATION: Allows the Agent to hot-swap code in the running process.
    WARNING: In production, this requires strict sandboxing.
    """
    try:
        # Create a temporary local scope to execute the new code
        local_scope = {}
        exec(python_code, {}, local_scope)
        
        # Find the new function in the executed scope
        new_func = None
        for key, value in local_scope.items():
            if isinstance(value, types.FunctionType):
                new_func = value
                break
        
        if not new_func:
            return "Error: No function definition found in the provided code."

        # Update the registry
        FUNCTION_REGISTRY[function_name] = new_func
        return f"Success: '{function_name}' has been hot-patched with new logic."
        
    except Exception as e:
        return f"Patch Failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()
