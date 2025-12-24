#!/usr/bin/env python3
"""
Auto-Healing Wrapper - Integrates skill_builder with error handling
Maintains flow with minimal attention by auto-applying learned resolutions
"""
import sys
import traceback
from skill_builder import SkillBuilder, auto_resolve

class AutoHealContext:
    """Context manager for automatic error resolution"""

    def __init__(self, operation_name="operation"):
        self.operation = operation_name
        self.builder = SkillBuilder()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            return False  # No error occurred

        # Extract error details
        error_type = exc_type.__name__
        error_msg = str(exc_val)

        # Try to auto-resolve
        resolution = auto_resolve(error_type, error_msg, self.operation)

        if resolution:
            print(f"✅ Auto-resolved: {self.operation}")
            return True  # Suppress error
        else:
            print(f"❌ New error pattern - capturing for future resolution")
            print(f"   Operation: {self.operation}")
            print(f"   Error: {error_type}: {error_msg}")
            return False  # Propagate error for manual handling

def with_auto_heal(func):
    """Decorator for automatic error handling"""
    def wrapper(*args, **kwargs):
        with AutoHealContext(func.__name__):
            return func(*args, **kwargs)
    return wrapper

# Example usage
if __name__ == "__main__":
    # Test 1: Known error (should auto-resolve)
    print("Test 1: Simulating known error pattern")
    with AutoHealContext("youtube_transcript_fetch"):
        # This would trigger AttributeError pattern
        raise AttributeError("'YouTubeTranscriptApi' has no attribute 'get_transcript'")

    print("\n" + "="*50 + "\n")

    # Test 2: New error (should capture)
    print("Test 2: New error pattern")
    try:
        with AutoHealContext("new_operation"):
            raise ValueError("Sample new error for learning")
    except ValueError as e:
        print(f"   Captured: {e}")

    print("\n" + "="*50 + "\n")

    # Show stats
    builder = SkillBuilder()
    print("📊 Current Stats:")
    print(f"   Total skills: {len(builder.skills['skills'])}")
    print(f"   Auto-resolved: {builder.get_stats()['auto_resolved']}")
    print(f"   Total errors: {builder.get_stats()['total_errors_handled']}")
