import time
import cProfile
import pstats
import io
import types
import inspect
import ast
import os
from mcp.server.fastmcp import FastMCP

# Initialize the MCP Server
mcp = FastMCP("PerformanceOptimizer")

# --- The Codebase (Dynamic Registry) ---
# We use a mutable dictionary so we can swap implementations at runtime.

def slow_fibonacci(n: int) -> int:
    if n <= 1: return n
    return slow_fibonacci(n-1) + slow_fibonacci(n-2)

FUNCTION_REGISTRY = {
    "slow_fibonacci": slow_fibonacci,
    "target_function": slow_fibonacci # Alias for the agent
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
        
        # Also update the alias if we patched the specific function
        if function_name == "slow_fibonacci":
            FUNCTION_REGISTRY["target_function"] = new_func
        # Or vice versa if we patched the alias, map it back (though less reliable without metadata)
        if function_name == "target_function":
             FUNCTION_REGISTRY["slow_fibonacci"] = new_func

        return f"Success: '{function_name}' has been hot-patched with new logic."
        
    except Exception as e:
        return f"Patch Failed: {str(e)}"

@mcp.tool()
def persist_optimization(function_name: str) -> str:
    """
    Commits the currently hot-patched function in memory to the actual source file on disk.
    Uses introspection to locate the original source lines and replaces them.
    """
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: '{function_name}' is not in the registry."
    
    # Get the function object (which is currently the optimized version in memory)
    func_obj = FUNCTION_REGISTRY[function_name]
    
    try:
        # 1. Get the source code of the NEW (optimized) function
        new_source = inspect.getsource(func_obj)
        
        # 2. We need to find where the OLD function was defined.
        # For this implementation, we assume the file is known or passed in context.
        target_file = __file__  # Self-modifying for this demo
        
        with open(target_file, 'r') as f:
            lines = f.readlines()
        
        # 3. Parse the file to find the original function definition
        # We use AST to find the line numbers of the function named 'function_name'
        with open(target_file, 'r') as f:
            tree = ast.parse(f.read())
            
        target_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                target_node = node
                break
        
        if not target_node:
            return f"Error: Could not locate original function definition for '{function_name}' in source file."
            
        # 4. Surgical Replacement
        # Calculate start and end lines (1-based index to 0-based list index)
        start_line = target_node.lineno - 1
        end_line = target_node.end_lineno
        
        # Prepare the new source (ensure indentation matches context if needed)
        # For simplicity, we assume top-level or consistent indentation here.
        
        print(f"Replacing lines {start_line+1}-{end_line} in {target_file}")
        
        # Replace the lines
        lines[start_line:end_line] = [new_source + "\n"]
        
        # 5. Write back to disk
        with open(target_file, 'w') as f:
            f.writelines(lines)
            
        return f"Success: Optimized source code written to {target_file}."

    except Exception as e:
        return f"Persistence Failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()
