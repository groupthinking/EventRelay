import time
import cProfile
import pstats
import io
import types
import inspect
import ast
import os
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PerformanceOptimizer")

# --- State Management ---


def slow_fibonacci(n: int) -> int:
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Registry for executable functions
FUNCTION_REGISTRY = {
    "slow_fibonacci": slow_fibonacci
}

# INNOVATION: Staging Area
# Stores the raw source code of patches that are active in memory 
# but not yet committed to disk.
PENDING_PATCHES = {}

# --- MCP Tools ---

@mcp.tool()
def run_benchmark(function_name: str, input_value: int, iterations: int = 1) -> str:
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: Function '{function_name}' not found."
    
    func = FUNCTION_REGISTRY[function_name]
    try:
        start_time = time.perf_counter()
        for _ in range(iterations):
            func(input_value)
        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / iterations
        return f"Benchmark Result: {function_name}({input_value}) took {avg_time:.6f} seconds."
    except Exception as e:
        return f"Runtime Error during benchmark: {str(e)}"

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
    Hot-swaps a function in memory and stages the source code for persistence.
    """
    try:
        # 1. Execute the new code in a temporary scope
        local_scope = {}
        exec(python_code, {}, local_scope)
        
        # 2. Extract the new function object
        new_func = None
        for key, value in local_scope.items():
            if isinstance(value, types.FunctionType):
                new_func = value
                break
        
        if not new_func:
            return "Error: No function definition found in the provided code."

        # 3. Update Runtime Registry (Hot Swap)
        FUNCTION_REGISTRY[function_name] = new_func
        
        # 4. Update Staging Area (For Persistence)
        PENDING_PATCHES[function_name] = python_code
        
        return f"Success: '{function_name}' has been hot-patched and staged for commit."
        
    except Exception as e:
        return f"Patch Failed: {str(e)}"

@mcp.tool()
def persist_optimization(function_name: str) -> str:
    """
    Commits the staged source code to the actual file on disk using AST parsing.
    """
    # 1. Retrieve the Source Code
    if function_name in PENDING_PATCHES:
        # Priority: Get from Staging Area (it was just patched)
        new_source = PENDING_PATCHES[function_name]
    elif function_name in FUNCTION_REGISTRY:
        # Fallback: Try to inspect existing function (if it wasn't patched dynamically)
        try:
            new_source = inspect.getsource(FUNCTION_REGISTRY[function_name])
        except OSError:
            return "Error: Cannot retrieve source. Function is dynamic and not in Staging Area."
    else:
        return f"Error: '{function_name}' is unknown."

    # 2. Locate the Target File
    # In a real app, you might track file paths in a metadata dict.
    # Here, we assume we are modifying this very file.
    target_file = __file__ 
    
    try:
        with open(target_file, 'r') as f:
            source_content = f.read()
        
        # 3. Parse AST to find the original function's location
        tree = ast.parse(source_content)
        target_node = None
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                target_node = node
                break
        
        if not target_node:
            return f"Error: Could not find definition of '{function_name}' in {target_file}."

        # 4. Surgical Replacement
        lines = source_content.splitlines(keepends=True)
        
        # Calculate line numbers (AST is 1-based, list is 0-based)
        start_index = target_node.lineno - 1
        end_index = target_node.end_lineno
        
        # Ensure new source ends with a newline if needed
        if not new_source.endswith('\n'):
            new_source += '\n'

        print(f"Replacing lines {start_index+1} to {end_index} in {target_file}")
        
        # Replace the block
        # We replace the entire range with the new source string
        lines[start_index:end_index] = [new_source]
        
        # 5. Write to Disk
        with open(target_file, 'w') as f:
            f.writelines(lines)
            
        # Clear from staging since it's now permanent
        if function_name in PENDING_PATCHES:
            del PENDING_PATCHES[function_name]
            
        return f"Success: Optimized source code written to {target_file}."

    except Exception as e:
        return f"Persistence Failed: {str(e)}"

if __name__ == "__main__":
    mcp.run()
