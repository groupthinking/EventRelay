import inspect
import os
import sys

# Add path to load profiling_server
sys.path.append(os.path.join(os.getcwd(), 'mcp-servers/mcp-profiling'))

try:
    import profiling_server
    print("[OK] profiling_server.py found and imported.")
except ImportError:
    print("[FAIL] profiling_server.py NOT found.")
    sys.exit(1)

def verify_fibonacci():
    print("\n--- Verifying slow_fibonacci ---")
    if 'slow_fibonacci' in profiling_server.FUNCTION_REGISTRY:
        func = profiling_server.FUNCTION_REGISTRY['slow_fibonacci']
        source = inspect.getsource(func)
        print(f"Source code preview:\n{source.strip()}")
        
        if "for _ in range" in source:
             print("\n[FINDING] slow_fibonacci is ITERATIVE (Fast). The 'slow' label is misleading.")
        elif "slow_fibonacci" in source and "return" in source and "(" in source: # Weak recursion check
             print("\n[FINDING] slow_fibonacci appears RECURSIVE (Slow).")
        else:
             print("\n[FINDING] logic Unclear.")
    else:
        print("[FAIL] slow_fibonacci NOT in registry.")

def verify_auditor():
    print("\n--- Verifying Auditor ---")
    if hasattr(profiling_server, 'audit_codebase'):
         print("[OK] audit_codebase function exists.")
    else:
         print("[FAIL] audit_codebase function MISSING.")

if __name__ == "__main__":
    verify_fibonacci()
    verify_auditor()
