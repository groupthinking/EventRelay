import profiling_server
import sys
import os

func_name = "slow_fibonacci"

# Ensure we are in the right directory or path setup
sys.path.append(os.getcwd())

print(f"--- 1. Generating Parity Tests for {func_name} ---")
# Inputs: 1, 2, 5, 10, 20
print(profiling_server.generate_parity_tests(func_name, [1, 2, 5, 10, 20]))

print(f"\n--- 2. Benchmarking Baseline (n=25) ---")
# Recursive 25 is fast enough (~10ms-100ms) but measurable. 30 might take 0.5s.
print(profiling_server.run_benchmark(func_name, 25))

print(f"\n--- 3. Submitting Patch ---")
# Iterative implementation
patch_code = """
def slow_fibonacci(n):
    # Optimized Iterative implementation
    if n <= 1: return n
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a
"""
result = profiling_server.submit_patch(func_name, patch_code)
print(result)

if "Success" not in result:
    print("Failed to patch!")
    sys.exit(1)

print(f"\n--- 4. Verifying Parity ---")
print(profiling_server.verify_parity(func_name))

print(f"\n--- 5. Benchmarking Optimized (n=25) ---")
print(profiling_server.run_benchmark(func_name, 25))

print(f"\n--- 6. Persisting Optimization (Safe) ---")
# This will modify profiling_server.py on disk
print(profiling_server.persist_optimization_safe(func_name))
