import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("DEBUG: Script started", flush=True)

try:
    print("DEBUG: Importing tools...", flush=True)
    from tools import get_aging_report
    print("DEBUG: Tools imported", flush=True)
    
    print("DEBUG: Importing runner...", flush=True)
    from harness.runner import section, summarize
    print("DEBUG: Runner imported", flush=True)
    
    print("DEBUG: Running test...", flush=True)
    section("TEST AGING REPORT")
    result = get_aging_report()
    print(f"DEBUG: Got result with keys: {result.keys()}", flush=True)
    print(f"  ✓ Test passed", flush=True)
    
    print("DEBUG: About to summarize", flush=True)
    summarize()
    
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}", flush=True)
    import traceback
    traceback.print_exc()
