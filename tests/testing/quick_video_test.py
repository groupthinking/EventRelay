#!/usr/bin/env python3
"""
Quick Video Test - Just Change the URL
======================================
"""
import sys
import asyncio

# 🎯 PASTE YOUR VIDEO URL HERE:
YOUR_VIDEO_URL = "https://www.youtube.com/watch?v=bMknfKXIFA8"

# 📺 OR USE ONE OF THESE EXAMPLES:
# YOUR_VIDEO_URL = "https://www.youtube.com/watch?v=x4rFhThSX04"  # Updated React Course
# YOUR_VIDEO_URL = "https://www.youtube.com/watch?v=_uQrJ0TkZlc"  # Python Tutorial
# YOUR_VIDEO_URL = "https://www.youtube.com/watch?v=hdI2bqOjy3c"  # JavaScript Course

async def main():
    """Quick test of your video"""

    # Import the analyzer
    from video_intelligence_lite import VideoIntelligenceAnalyzer

    print(f"🎯 Testing: {YOUR_VIDEO_URL}")
    print("🧠 Running video intelligence analysis...")

    analyzer = VideoIntelligenceAnalyzer()
    intelligence = await analyzer.analyze_video_intelligence(YOUR_VIDEO_URL)

    # Quick summary
    print(f"\n✅ QUICK RESULTS:")
    print(f"📺 {intelligence.title[:60]}...")
    print(f"🎓 Educational Score: {intelligence.educational_score:.2f}/1.0")
    print(f"😊 Sentiment: {intelligence.sentiment_label}")
    print(f"💻 Code Extraction: {'✅' if intelligence.code_extraction_potential else '❌'}")
    print(f"📝 Quiz Potential: {'✅' if intelligence.quiz_generation_potential else '❌'}")
    print(f"\n🎉 Full analysis saved to: video_intelligence_{intelligence.video_id}.json")

if __name__ == "__main__":
    asyncio.run(main())