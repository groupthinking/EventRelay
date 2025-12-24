#!/usr/bin/env python3
"""
Test MCP Tool: youtube-uvai-processor
Direct invocation to validate MCP server functionality
"""
import sys
import json
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import the MCP server module
import youtube_uvai_mcp

def test_extract_video_id():
    """Test: extract_video_id tool"""
    print("=" * 70)
    print("Test 1: extract_video_id")
    print("=" * 70)

    test_url = "https://youtu.be/jawdcPoZJmI"
    print(f"Input: {test_url}")

    result = youtube_uvai_mcp.extract_video_id(test_url)
    print(f"Result: {json.dumps(result, indent=2)}")

    assert result["video_id"] == "jawdcPoZJmI", "Video ID extraction failed"
    print("✅ PASSED\n")
    return result

def test_get_video_metadata():
    """Test: get_video_metadata tool"""
    print("=" * 70)
    print("Test 2: get_video_metadata")
    print("=" * 70)

    video_id = "jawdcPoZJmI"
    print(f"Video ID: {video_id}")

    result = youtube_uvai_mcp.get_video_metadata(video_id)
    print(f"Result keys: {list(result.keys())}")

    if "error" not in result:
        print(f"✅ Title: {result.get('title', 'N/A')}")
        print(f"✅ Duration: {result.get('duration', 'N/A')}")
        print("✅ PASSED\n")
    else:
        print(f"⚠️  Warning: {result['error']}")
        print("Note: Metadata API may require additional setup\n")

    return result

def test_get_video_transcript():
    """Test: get_video_transcript tool (cached transcript)"""
    print("=" * 70)
    print("Test 3: get_video_transcript")
    print("=" * 70)

    video_id = "jawdcPoZJmI"
    print(f"Video ID: {video_id}")

    result = youtube_uvai_mcp.get_video_transcript(video_id)

    if "error" not in result:
        transcript = result.get("transcript", [])
        word_count = len(" ".join([seg.get("text", "") for seg in transcript]).split())
        print(f"✅ Segments: {len(transcript)}")
        print(f"✅ Word count: {word_count}")
        print("✅ PASSED\n")
    else:
        print(f"❌ Error: {result['error']}\n")

    return result

if __name__ == "__main__":
    print("\n🧪 MCP Tool Direct Test Suite\n")
    print("Testing youtube-uvai-processor MCP server tools\n")

    results = {}

    # Test 1: Extract video ID
    try:
        results["extract_video_id"] = test_extract_video_id()
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}\n")
        results["extract_video_id"] = {"error": str(e)}

    # Test 2: Get video metadata
    try:
        results["get_video_metadata"] = test_get_video_metadata()
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}\n")
        results["get_video_metadata"] = {"error": str(e)}

    # Test 3: Get transcript (uses caching)
    try:
        results["get_video_transcript"] = test_get_video_transcript()
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}\n")
        results["get_video_transcript"] = {"error": str(e)}

    # Summary
    print("=" * 70)
    print("🎯 TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in results.values() if "error" not in r)
    total = len(results)

    print(f"Tests Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED - MCP Server Functional")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed or require additional setup")

    print("\n📋 MCP Server Status:")
    print("   - extract_video_id: ✅" if "error" not in results.get("extract_video_id", {}) else "   - extract_video_id: ❌")
    print("   - get_video_metadata: ✅" if "error" not in results.get("get_video_metadata", {}) else "   - get_video_metadata: ⚠️")
    print("   - get_video_transcript: ✅" if "error" not in results.get("get_video_transcript", {}) else "   - get_video_transcript: ❌")
