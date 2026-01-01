#!/usr/bin/env python3
"""
Command Line Video Analyzer
============================
Usage: python3 analyze_video.py "https://www.youtube.com/watch?v=VIDEO_ID"
"""
import sys
import asyncio

async def main():
    """Analyze video from command line argument"""

    if len(sys.argv) < 2:
        print("🎯 VIDEO ANALYZER")
        print("=" * 40)
        print("Usage: python3 analyze_video.py \"YOUR_VIDEO_URL\"")
        print("\n📺 Example:")
        print('python3 analyze_video.py "https://www.youtube.com/watch?v=bMknfKXIFA8"')
        print("\n🔗 Or try these examples:")
        print("• React: https://www.youtube.com/watch?v=x4rFhThSX04")
        print("• Python: https://www.youtube.com/watch?v=_uQrJ0TkZlc")
        print("• JavaScript: https://www.youtube.com/watch?v=hdI2bqOjy3c")
        return

    video_url = sys.argv[1]

    # Import the analyzer
    from video_intelligence_lite import VideoIntelligenceAnalyzer

    print(f"🎯 Analyzing: {video_url}")

    try:
        analyzer = VideoIntelligenceAnalyzer()
        intelligence = await analyzer.analyze_video_intelligence(video_url)

        print(f"\n🎉 ANALYSIS COMPLETE!")
        print(f"📺 {intelligence.title}")
        print(f"🎓 Educational Score: {intelligence.educational_score:.2f}/1.0")
        print(f"😊 Community Sentiment: {intelligence.sentiment_label}")
        print(f"💬 Comments Analyzed: {intelligence.comments_analyzed}")
        print(f"💻 Code Extraction Potential: {'✅ YES' if intelligence.code_extraction_potential else '❌ NO'}")

        filename = f"analysis_{intelligence.video_id}.json"
        import json
        from dataclasses import asdict
        with open(filename, 'w') as f:
            json.dump(asdict(intelligence), f, indent=2)

        print(f"💾 Full report: {filename}")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure the video URL is public and correctly formatted")

if __name__ == "__main__":
    asyncio.run(main())