#!/usr/bin/env python3
"""
Integration Verification Script
"""
import sys
import os

print("🔍 Starting Integration Verification...")

# Setup paths
base_dir = "/Users/garvey/Dev/OpenAI_Hub/mcp-servers"
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "lib"))
sys.path.append(os.path.join(base_dir, "servers"))

try:
    print("   Checking StateFabric...")
    from shared_state import fabric
    print("   ✅ StateFabric imported")
except ImportError as e:
    print(f"   ❌ StateFabric import failed: {e}")

try:
    print("   Checking Video Agent Server...")
    import video_agent_server
    print("   ✅ Video Agent Server imported")
except ImportError as e:
    print(f"   ❌ Video Agent Server import failed: {e}")

try:
    print("   Checking Code Analysis Server...")
    import code_analysis_server
    print("   ✅ Code Analysis Server imported")
except ImportError as e:
    print(f"   ❌ Code Analysis Server import failed: {e}")

print("Verification Complete.")
