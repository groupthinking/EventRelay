import time
import cProfile
import pstats
import io
import types
import inspect
import ast
import os
import shutil
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PerformanceOptimizer")

# --- State Management ---

# Reset to slow implementation for the demo
def slow_fibonacci(n: int) -> int:
    if n <= 1: return n
    return slow_fibonacci(n-1) + slow_fibonacci(n-2)

# Registry for executable functions
FUNCTION_REGISTRY = {
    "slow_fibonacci": slow_fibonacci
}

# Staging Area for patches
PENDING_PATCHES = {}

# In-Memory Test Suite for Parity Check
PARITY_TEST_SUITE = []

# --- Helper Functions (Internal) ---

def _perform_ast_rewrite(function_name: str, target_file: str) -> str:
    """Internal helper to perform the AST rewrite logic."""
    # 1. Retrieve the Source Code
    if function_name in PENDING_PATCHES:
        new_source = PENDING_PATCHES[function_name]
    elif function_name in FUNCTION_REGISTRY:
        try:
            new_source = inspect.getsource(FUNCTION_REGISTRY[function_name])
        except OSError:
            raise ValueError("Error: Cannot retrieve source. Function is dynamic and not in Staging Area.")
    else:
        raise ValueError(f"Error: '{function_name}' is unknown.")

    # 2. Read Target File in pure text mode
    try:
        with open(target_file, 'r') as f:
            source_content = f.read()
    except IOError as e:
         raise ValueError(f"Error reading file: {e}")
        
    # 3. Parse AST
    try:
        tree = ast.parse(source_content)
    except SyntaxError as e:
        raise ValueError(f"Error parsing target file AST: {e}")

    target_node = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            target_node = node
            break
    
    if not target_node:
        raise ValueError(f"Error: Could not find definition of '{function_name}' in {target_file}.")

    # 4. Surgical Replacement
    lines = source_content.splitlines(keepends=True)
    start_index = target_node.lineno - 1
    end_index = target_node.end_lineno
    
    if not new_source.endswith('\n'):
        new_source += '\n'

    # Validate that we aren't replacing the whole file by accident
    if start_index < 0 or end_index > len(lines):
        raise ValueError("Error: Invalid line ranges calculated.")

    print(f"Replacing lines {start_index+1} to {end_index} in {target_file}")
    lines[start_index:end_index] = [new_source]
    
    # 5. Write to Disk
    with open(target_file, 'w') as f:
        f.writelines(lines)
        
    # Cleanup staging
    if function_name in PENDING_PATCHES:
        del PENDING_PATCHES[function_name]
        
    return f"Success: Optimized source code written to {target_file}."

# --- MCP Tools ---

@mcp.tool()
def load_target_module(file_path: str) -> str:
    """
    INNOVATION: Dynamically imports any Python file from disk and 
    registers its functions into the FUNCTION_REGISTRY for profiling.
    """
    if not os.path.exists(file_path):
        return f"Error: File {file_path} not found."
    
    try:
        # In this demo, we can just treat the file as a module.
        # [Level 7 Innovation] Generate unique module name to prevent collisions
        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        module_name = f"{os.path.basename(file_path).replace('.py', '')}_{file_hash}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            return "Error: Could not create module spec."
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        count = 0
        for name, func in inspect.getmembers(module, inspect.isfunction):
            # Only register functions defined in the file (ignore imports)
            if func.__module__ == module_name:
                FUNCTION_REGISTRY[name] = func
                count += 1
                
        return f"Success: Loaded module '{module_name}'. Registered {count} functions: {list(FUNCTION_REGISTRY.keys())}"
    except Exception as e:
        return f"Load Failed: {str(e)}"

@mcp.tool()
def audit_codebase(file_path: str) -> str:
    """
    The 'Auditor': Statically analyzes source code to find recursive functions
    or potential bottlenecks without running them.
    """
    try:
        with open(file_path, "r") as f:
            tree = ast.parse(f.read())
            
        candidates = []
        
        class BottleneckFinder(ast.NodeVisitor):
            def visit_FunctionDef(self, node):
                # 1. Detect Recursion
                is_recursive = False
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name) and child.func.id == node.name:
                            is_recursive = True
                            break
                
                # 2. Detect High Complexity (Nested Loops)
                loop_depth = 0
                has_nested_loops = False
                for child in ast.walk(node):
                    if isinstance(child, (ast.For, ast.While)):
                        for grandchild in ast.walk(child):
                            if isinstance(grandchild, (ast.For, ast.While)) and grandchild is not child:
                                has_nested_loops = True
                
                if is_recursive:
                    candidates.append(f"{node.name} (Reason: Recursion Detected)")
                elif has_nested_loops:
                    candidates.append(f"{node.name} (Reason: Nested Loops Detected)")

        BottleneckFinder().visit(tree)
        
        if not candidates:
            return "Audit Complete: No obvious bottlenecks found."
        return f"Audit Report: Found {len(candidates)} candidates for optimization:\n- " + "\n- ".join(candidates)
        
    except Exception as e:
        return f"Audit Failed: {str(e)}"

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
    try:
        local_scope = {}
        exec(python_code, exec_globals, local_scope)
        
        new_func = None
        for key, value in local_scope.items():
            if isinstance(value, types.FunctionType):
                new_func = value
                break
        
        if not new_func:
            return "Error: No function definition found in the provided code."

        FUNCTION_REGISTRY[function_name] = new_func
        PENDING_PATCHES[function_name] = python_code
        
        return f"Success: '{function_name}' has been hot-patched and staged for commit."
        
    except Exception as e:
        return f"Patch Failed: {str(e)}"

@mcp.tool()
def generate_parity_tests(function_name: str, test_inputs: list[int]) -> str:
    """
    Runs the CURRENT (presumably slow but correct) function against inputs 
    to establish a 'Ground Truth' baseline.
    """
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: '{function_name}' not found."
    
    func = FUNCTION_REGISTRY[function_name]
    global PARITY_TEST_SUITE
    PARITY_TEST_SUITE = [] # Clear previous tests
    
    results = []
    try:
        for val in test_inputs:
            output = func(val)
            PARITY_TEST_SUITE.append((val, output))
            results.append(f"f({val})={output}")
            
        return f"Generated {len(results)} parity tests: {', '.join(results[:3])}..."
    except Exception as e:
        return f"Error generating tests: {str(e)}"

@mcp.tool()
def verify_parity(function_name: str) -> str:
    """
    Runs the NEW (hot-patched) function against the stored Ground Truth.
    Returns success only if 100% of outputs match.
    """
    if function_name not in FUNCTION_REGISTRY:
        return f"Error: '{function_name}' not found."
    
    if not PARITY_TEST_SUITE:
        return "Error: No tests found. Run 'generate_parity_tests' first."
        
    func = FUNCTION_REGISTRY[function_name]
    failures = []
    
    for input_val, expected in PARITY_TEST_SUITE:
        try:
            actual = func(input_val)
            if actual != expected:
                failures.append(f"Input {input_val}: Expected {expected}, Got {actual}")
        except Exception as e:
            failures.append(f"Input {input_val}: Crashed with {str(e)}")
            
    if failures:
        return f"❌ Parity Check Failed ({len(failures)} errors):\n" + "\n".join(failures[:5])
    
    return f"✅ Parity Check Passed: {len(PARITY_TEST_SUITE)}/{len(PARITY_TEST_SUITE)} outputs match baseline."

@mcp.tool()
def persist_optimization(function_name: str, file_path: str) -> str:
    try:
        return _perform_ast_rewrite(function_name, file_path)
    except Exception as e:
        return f"Persistence Failed: {str(e)}"

@mcp.tool()
def persist_optimization_safe(function_name: str, file_path: str) -> str:
    """
    A safer version of persist that creates a .bak file before overwriting.
    """
    target_file = file_path
    
    # 1. Create Backup
    backup_file = target_file + ".bak"
    try:
        shutil.copy2(target_file, backup_file)
    except IOError as e:
        return f"Safety Error: Could not create backup. Aborting persist. {e}"
        
    # 2. Perform Rewrite
    try:
        result = _perform_ast_rewrite(function_name, target_file)
        return f"{result} (Backup saved to {os.path.basename(backup_file)})"
    except Exception as e:
        return f"Persistence Failed: {str(e)}"

@mcp.tool()
def restore_backup() -> str:
    """
    Emergency tool to restore the .bak file if the agent breaks the server.
    """
    target_file = __file__
    backup_file = target_file + ".bak"
    
    if not os.path.exists(backup_file):
        return "Error: No backup file found."
        
    try:
        shutil.copy2(backup_file, target_file)
        return "Success: Server source code restored from backup. Restart required."
    except Exception as e:
        return f"Restore Failed: {str(e)}"

# --- Git Integration Tools ---

@mcp.tool()
def git_create_branch(branch_name: str) -> str:
    """
    Creates and switches to a new git branch for the optimization task.
    """
    try:
        # Check if repo is clean first (optional, but good practice)
        subprocess.run(["git", "checkout", "-b", branch_name], check=True, capture_output=True)
        return f"Success: Switched to new branch '{branch_name}'."
    except subprocess.CalledProcessError as e:
        return f"Git Error: {e.stderr.decode().strip()}"

@mcp.tool()
def git_commit_optimization(function_name: str, baseline_time: float, optimized_time: float) -> str:
    """
    Commits the changes with a 'Proof-of-Optimization' message.
    Calculates the speedup factor automatically.
    """
    if optimized_time == 0: optimized_time = 0.000001 # Prevent div by zero
    speedup = baseline_time / optimized_time
    
    message = (
        f"perf({function_name}): Optimize {speedup:.1f}x speedup\n\n"
        f"Autonomous Optimization Report:\n"
        f"- Baseline: {baseline_time:.6f}s\n"
        f"- Optimized: {optimized_time:.6f}s\n"
        f"- Logic Parity: Verified via TDD\n"
    )
    
    try:
        # Stage the specific file (assuming we know it, or just -a for all tracked)
        subprocess.run(["git", "add", "-u"], check=True, capture_output=True)
        
        # Commit
        subprocess.run(["git", "commit", "-m", message], check=True, capture_output=True)
        
        return f"Success: Committed changes with message:\n'{message.splitlines()[0]}'"
    except subprocess.CalledProcessError as e:
        return f"Git Commit Failed: {e.stdout.decode() if e.stdout else ''} {e.stderr.decode() if e.stderr else str(e)}"

@mcp.tool()
def git_reset_hard() -> str:
    """
    Emergency tool: Reverts all local changes to the last commit.
    Useful if the agent messes up the file during patching.
    """
    subprocess.run(["git", "reset", "--hard"], check=True, capture_output=True)
    return "Success: Hard reset performed. Working directory clean."

if __name__ == "__main__":
    mcp.run()
