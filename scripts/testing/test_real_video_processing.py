#!/usr/bin/env python3
"""
REAL VIDEO PROCESSING TEST

Tests actual video processing to verify if it's using real APIs or mock fallbacks
"""

import asyncio
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_real_video_processing():
    """Test real video processing with actual APIs"""
    try:
        # Import the real video processor
        from src.youtube_extension.backend.services.real_video_processor import (
            RealVideoProcessor,
        )

        # Test video URL - Business-focused content
        test_video_url = "https://www.youtube.com/watch?v=hvL1339luv0"  # Python tutorial (business-relevant)

        print("🎬 Testing Real Video Processing...")
        print(f"Video URL: {test_video_url}")

        # Initialize processor
        processor = RealVideoProcessor()

        # Process video
        print("\n🚀 Starting video processing...")
        start_time = asyncio.get_event_loop().time()

        result = await processor.process_video(test_video_url)

        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time

        print("\n✅ Processing completed!")
        print(f"Processing time: {processing_time:.2f} seconds")
        print(f"Result keys: {list(result.keys()) if result else 'None'}")

        # Analyze result to check if it's real or mock
        if result:
            print("\n🔍 Analyzing result...")

            # Check for mock indicators
            method = result.get('method', 'unknown')
            print(f"Processing method: {method}")

            if method == 'mock':
                print("❌ MOCK DETECTED: System is using mock fallbacks!")
                return False, "Mock implementation detected"

            # Check for real data
            if 'transcript' in result:
                transcript_length = len(result['transcript'])
                print(f"✅ Real transcript found: {transcript_length} characters")

            if 'analysis' in result:
                analysis_keys = list(result['analysis'].keys())
                print(f"✅ Real analysis found: {analysis_keys}")

            if 'metadata' in result:
                metadata_keys = list(result['metadata'].keys())
                print(f"✅ Real metadata found: {metadata_keys}")

            # Check processing time (mock would be instant)
            if processing_time < 1.0:
                print("⚠️ WARNING: Processing too fast - might be mock!")
                return False, "Processing too fast for real API calls"

            print("✅ REAL PROCESSING DETECTED: System is using actual APIs!")
            return True, f"Real processing completed in {processing_time:.2f}s"

        else:
            print("❌ No result returned")
            return False, "No processing result"

    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        return False, str(e)

async def main():
    print("🔬 REAL VIDEO PROCESSING VERIFICATION")
    print("=" * 50)

    success, message = await test_real_video_processing()

    print("\n" + "=" * 50)
    print("📊 VERIFICATION RESULT:")

    if success:
        print("✅ REAL VIDEO PROCESSING: WORKING CORRECTLY")
        print(f"Details: {message}")
    else:
        print("❌ REAL VIDEO PROCESSING: FAILED OR USING MOCKS")
        print(f"Issue: {message}")

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
