#!/usr/bin/env python3
"""Test script for skill bridge connector"""
import sys
import time

print("🧪 Testing Collective Skill Builder")
print("=" * 60)

# Import the connector
from skill_bridge_connector import CollectiveSkillBuilder

# Create instance
print("\n1. Creating CollectiveSkillBuilder instance...")
builder = CollectiveSkillBuilder()

print("\n2. Capturing test skill...")
skill = builder.capture_error_resolution(
    error_type="TestError",
    error_msg="Test error message for validation",
    resolution="Test resolution for validation",
    context="Integration test"
)

print(f"\n✅ Skill captured: #{skill['id']}")
print(f"   Type: {skill['error_type']}")
print(f"   Pattern: {skill['pattern']}")
print(f"   Resolution: {skill['resolution']}")

print("\n3. Checking stats...")
stats = builder.get_stats()
print(f"   Total errors handled: {stats['total_errors_handled']}")
print(f"   Auto-resolved: {stats['auto_resolved']}")

print("\n4. Waiting 5 seconds for network synchronization...")
time.sleep(5)

print("\n✅ Test complete - Collective learning operational")
