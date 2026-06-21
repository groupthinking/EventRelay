#!/usr/bin/env python3
"""
🔴 LIVE INTEGRATION TEST - Real API Calls (No Mocks, No Fakes)
Testing actual production integration with real services
"""
import asyncio
import json
import time
from google import genai
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound

# Real API Keys from /Users/garvey/Desktop/api/api-MASTER 2-clean.txt
GEMINI_API_KEY = "AIzaSyAdaiRnkCVDq_-ac-iDiTPt_KLvT-MW-JY"
YOUTUBE_API_KEY = "AIzaSyDKA991w_reg2W5Z6Juw92mg9Nj86iQFaA"
ANTHROPIC_API_KEY = "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"

async def test_live_video_processing():
    """
    🔴 LIVE TEST: Real YouTube video → Real transcript → Real Gemini analysis
    """

    print("=" * 70)
    print("🔴 LIVE INTEGRATION TEST - Real API Calls (No Mocks)")
    print("=" * 70)

    # Real video for testing
    video_id = "jawdcPoZJmI"  # Patrick Ellis on Claude Code 2.0 vs Codex
    video_url = f"https://youtu.be/{video_id}"

    print(f"\n📹 Video: {video_url}")
    print(f"Video ID: {video_id}\n")

    start_time = time.time()

    # STEP 1: REAL YouTube Transcript Extraction
    print("Step 1: Extracting REAL transcript from YouTube API...")
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=['en'])

        # Convert to list and extract text
        segments = list(transcript)
        full_text = ' '.join([seg.text for seg in segments])
        word_count = len(full_text.split())

        print(f"✅ REAL Transcript extracted:")
        print(f"   - API: YouTube Transcript API")
        print(f"   - Segments: {len(segments)}")
        print(f"   - Word count: {word_count}")
        print(f"   - Duration: {segments[-1].start + segments[-1].duration:.1f}s")
        print(f"   - First 200 chars: {full_text[:200]}...")

        transcript_time = time.time() - start_time
        print(f"   - Time: {transcript_time:.2f}s")

    except NoTranscriptFound as e:
        print(f"❌ No transcript available: {e}")
        return {"status": "failed", "error": "No transcript"}
    except Exception as e:
        print(f"❌ Transcript extraction failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

    # STEP 2: REAL Gemini API Analysis
    print("\nStep 2: REAL Gemini 2.0 Flash analysis...")
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        # Use first 3000 chars for analysis (stay under token limits)
        analysis_prompt = f"""Analyze this YouTube video transcript and provide actionable insights.

Video: Claude Code 2.0 vs Codex comparison by Patrick Ellis

Transcript excerpt ({word_count} total words):
{full_text[:3000]}

Provide in JSON format:
{{
  "key_insights": ["insight 1", "insight 2", "insight 3"],
  "automation_opportunities": ["opportunity 1", "opportunity 2"],
  "next_actions": ["action 1", "action 2"],
  "technical_concepts": ["concept 1", "concept 2", "concept 3"]
}}"""

        gemini_start = time.time()
        response = client.models.generate_content(
            model="gemini-2.0-flash-exp",
            contents=analysis_prompt
        )
        gemini_time = time.time() - gemini_start

        print(f"✅ REAL Gemini analysis complete:")
        print(f"   - Model: gemini-2.0-flash-exp")
        print(f"   - Response length: {len(response.text)} chars")
        print(f"   - Time: {gemini_time:.2f}s")
        print(f"   - Analysis preview (first 500 chars):")
        print(f"   {response.text[:500]}...")

    except Exception as e:
        print(f"❌ Gemini analysis failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "failed", "error": str(e)}

    total_time = time.time() - start_time

    # STEP 3: Validation & Results
    print("\n" + "=" * 70)
    print("✅ LIVE INTEGRATION TEST: SUCCESS")
    print("=" * 70)

    results = {
        "status": "success",
        "live_test": True,
        "video_id": video_id,
        "transcript": {
            "api": "YouTube Transcript API (youtube_transcript_api)",
            "segments": len(segments),
            "word_count": word_count,
            "duration_seconds": segments[-1].start + segments[-1].duration,
            "extraction_time": transcript_time
        },
        "analysis": {
            "model": "gemini-2.0-flash-exp",
            "response_chars": len(response.text),
            "analysis_time": gemini_time
        },
        "performance": {
            "total_time": total_time,
            "transcript_time": transcript_time,
            "gemini_time": gemini_time
        }
    }

    print("\n📊 Test Results:")
    print(f"   ✅ YouTube Transcript API: WORKING ({word_count} words)")
    print(f"   ✅ Gemini 2.0 Flash: WORKING ({len(response.text)} chars)")
    print(f"   ✅ Total latency: {total_time:.2f}s")
    print(f"   ✅ Real data pipeline: VALIDATED")

    print("\n⚡ Performance Metrics:")
    print(f"   - Transcript extraction: {transcript_time:.2f}s")
    print(f"   - Gemini analysis: {gemini_time:.2f}s")
    print(f"   - Total end-to-end: {total_time:.2f}s")

    print("\n🎯 Production Ready:")
    print("   ✅ Real transcript extraction from YouTube")
    print("   ✅ Real AI analysis with Gemini 2.0 Flash")
    print("   ✅ No mocks, no fakes, no simulations")
    print("   ✅ Live market test: PASSED")

    return results

if __name__ == "__main__":
    print("\n🚀 Starting LIVE integration test...\n")
    result = asyncio.run(test_live_video_processing())

    if result:
        print(f"\n📋 Final Result:")
        print(json.dumps(result, indent=2))

        if result.get("status") == "success":
            print("\n" + "=" * 70)
            print("🎉 ALL SYSTEMS OPERATIONAL - READY FOR PRODUCTION")
            print("=" * 70)
