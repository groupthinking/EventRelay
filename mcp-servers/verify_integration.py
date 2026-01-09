#!/usr/bin/env python3
"""
Integration Verification Script
"""
import sys
import os

print("🔍 Starting Integration Verification...")

# Setup paths
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "python-suite"))
sys.path.append(os.path.join(base_dir, "mcp-profiling"))
sys.path.append(os.path.join(base_dir, "lib"))

import traceback

try:
    print("   Checking YouTube UVAI MCP...")
    import youtube_uvai_mcp

    print("   ✅ YouTube UVAI MCP imported")
except Exception:
    print(f"   ❌ YouTube UVAI MCP import failed:")
    traceback.print_exc()

try:
    print("   Checking Video Agent Server...")
    import video_agent_server

    print("   ✅ Video Agent Server imported")
except Exception:
    print(f"   ❌ Video Agent Server import failed:")
    traceback.print_exc()

try:
    print("   Checking Code Analysis Server...")
    import code_analysis_server

    print("   ✅ Code Analysis Server imported")
except Exception:
    print(f"   ❌ Code Analysis Server import failed:")
    traceback.print_exc()

print("Verification Complete.")
