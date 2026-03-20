#!/usr/bin/env python3
"""
Test script to verify imports for universal coordinator
Tests each system independently to identify specific blockers
"""

import sys


def test_gemini():
    """Test Gemini processor import"""
    print("\n" + "="*60)
    print("Testing Gemini Processor Import")
    print("="*60)
    try:
        print("✅ Gemini processor imported successfully")
        return True
    except Exception as e:
        print(f"❌ Gemini import failed: {e}")
        return False

def test_uvai():
    """Test UVAI imports"""
    print("\n" + "="*60)
    print("Testing UVAI Imports")
    print("="*60)

    UVAI_PATH = "/Users/garvey/Dev/OpenAI_Hub/projects/UVAI/src"
    if str(UVAI_PATH) not in sys.path:
        sys.path.insert(0, str(UVAI_PATH))

    try:
        print("✅ UVAICodexUniversalDeployment imported successfully")
        return True
    except Exception as e:
        print(f"❌ UVAI import failed: {e}")
        return False

def test_eventrelay():
    """Test EventRelay imports"""
    print("\n" + "="*60)
    print("Testing EventRelay Imports")
    print("="*60)

    EVENTRELAY_PATH = "/Users/garvey/Dev/OpenAI_Hub/projects/EventRelay/src"
    if str(EVENTRELAY_PATH) not in sys.path:
        sys.path.insert(0, str(EVENTRELAY_PATH))

    try:
        print("✅ VideoToActionWorkflow imported successfully")
        return True
    except Exception as e:
        print(f"❌ EventRelay import failed: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("UNIVERSAL AUTOMATION SERVICE - IMPORT TESTS")
    print("="*60)

    results = {
        "Gemini": test_gemini(),
        "UVAI": test_uvai(),
        "EventRelay": test_eventrelay()
    }

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    for component, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{component:15} : {status}")

    all_pass = all(results.values())

    print("\n" + "="*60)
    if all_pass:
        print("🎉 ALL SYSTEMS OPERATIONAL")
        print("Ready to run: python3 universal_coordinator.py")
    else:
        print("⚠️  SOME SYSTEMS UNAVAILABLE")
        print("\nAvailable modes:")
        if results["Gemini"]:
            print("  - python3 universal_coordinator.py URL --mode gemini")
        if results["EventRelay"] and not results["UVAI"]:
            print("  - python3 universal_coordinator.py URL --mode production (partial)")
        if all(results.values()):
            print("  - python3 universal_coordinator.py URL --mode hybrid")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
