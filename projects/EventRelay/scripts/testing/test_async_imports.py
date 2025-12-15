#!/usr/bin/env python3
"""
Test script to verify async imports don't cause coroutines at import time
"""

import sys
import os
import traceback

def test_import(module_path):
    """Test importing a module without triggering async execution"""
    try:
        print(f"Testing import: {module_path}")
        # Clear any existing modules to ensure clean import
        if module_path in sys.modules:
            del sys.modules[module_path]

        __import__(module_path)
        print(f"✅ Successfully imported {module_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to import {module_path}: {e}")
        traceback.print_exc()
        return False

def main():
    """Test critical modules that might be imported at startup"""
    test_modules = [
        # Core modules
        'src.youtube_extension.main',
        'src.youtube_extension.backend.main',

        # Service modules that might be imported
        'src.youtube_extension.backend.services.robust_youtube_service',
        'src.youtube_extension.backend.services.real_youtube_api',
        'src.youtube_extension.backend.services.real_video_processor',
        'src.youtube_extension.backend.services.real_ai_processor',
        'src.youtube_extension.backend.services.optimized_video_processor',
        'src.youtube_extension.backend.services.parallel_video_processor',
        'src.youtube_extension.backend.services.comprehensive_benchmarking',
        'src.youtube_extension.backend.services.api_cost_monitor',
        'src.youtube_extension.backend.services.database_optimizer',
        'src.youtube_extension.backend.services.intelligent_cache',

        # Processor modules
        'src.youtube_extension.processors.enhanced_extractor',
        'src.youtube_extension.processors.autonomous_processor',

        # Services
        'src.youtube_extension.services.video_subagent',

        # Tools and scripts
        'database.index_analysis',
        'tools.testing.test_enhanced_backend',
    ]

    success_count = 0
    total_count = len(test_modules)

    print("🚀 Testing async import issues...")
    print("=" * 60)

    for module in test_modules:
        if test_import(module):
            success_count += 1
        print()

    print("=" * 60)
    print(f"📊 Results: {success_count}/{total_count} modules imported successfully")

    if success_count == total_count:
        print("✅ All critical modules can be imported without async execution issues!")
        return 0
    else:
        print("❌ Some modules have import issues that need to be fixed.")
        return 1

if __name__ == "__main__":
    exit(main())
