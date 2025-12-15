#!/usr/bin/env python3
"""
BUSINESS WORKFLOW AUTOMATION TEST

Tests real business-focused video processing workflows
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_business_video_processing():
    """Test processing business-relevant educational content"""
    try:
        from src.youtube_extension.backend.services.real_video_processor import RealVideoProcessor

        # Business-focused educational content
        business_videos = [
            {
                "url": "https://www.youtube.com/watch?v=hvL1339luv0",
                "title": "Python Tutorial",
                "business_value": "Programming education for team development"
            },
            {
                "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
                "title": "Git Workflow",
                "business_value": "Version control best practices"
            }
        ]

        processor = RealVideoProcessor()
        results = []

        print("🏢 TESTING BUSINESS WORKFLOW AUTOMATION")
        print("=" * 60)

        for video_info in business_videos:
            print(f"\n📊 Processing: {video_info['title']}")
            print(f"   Business Value: {video_info['business_value']}")
            print(f"   URL: {video_info['url']}")

            start_time = asyncio.get_event_loop().time()

            try:
                result = await processor.process_video(video_info['url'])
                processing_time = asyncio.get_event_loop().time() - start_time

                # Analyze business-relevant metrics
                analysis = {
                    "title": video_info['title'],
                    "processing_time": processing_time,
                    "success": result.get('success', False),
                    "has_transcript": result.get('transcript', {}).get('has_transcript', False),
                    "ai_analysis_success": result.get('ai_analysis', {}).get('success', False),
                    "cost": result.get('cost_breakdown', {}).get('total_cost', 0),
                    "transcript_segments": result.get('transcript', {}).get('segment_count', 0),
                    "quality_score": len([k for k in ['metadata', 'transcript', 'ai_analysis']
                                        if result.get(k) is not None]) / 3
                }

                results.append(analysis)

                print("   ✅ Processing Complete:")
                print(f"   ⏱️  Processing Time: {analysis['processing_time']:.2f}s")
                print(f"   📝 Transcript: {'✅' if analysis['has_transcript'] else '❌'} ({analysis['transcript_segments']} segments)")
                print(f"   🤖 AI Analysis: {'✅' if analysis['ai_analysis_success'] else '❌'}")
                print(f"   💰 Cost: ${analysis['cost']:.4f}")
                print(f"   📊 Quality Score: {analysis['quality_score']:.2f}/1.0")

            except Exception as e:
                print(f"   ❌ Failed: {str(e)}")
                results.append({
                    "title": video_info['title'],
                    "processing_time": 0,
                    "success": False,
                    "error": str(e)
                })

        # Business workflow analysis
        print("\n" + "=" * 60)
        print("📈 BUSINESS WORKFLOW ANALYSIS")

        successful_processes = [r for r in results if r.get('success', False)]
        total_cost = sum(r.get('cost', 0) for r in results)
        avg_processing_time = sum(r.get('processing_time', 0) for r in results) / len(results)

        print("\n📊 Overall Metrics:")
        print(f"   Success Rate: {len(successful_processes)}/{len(results)} ({len(successful_processes)/len(results)*100:.1f}%)")
        print(f"   Average Processing Time: {avg_processing_time:.2f}s")
        print(f"   Total Cost: ${total_cost:.4f}")
        print(f"   Videos Processed: {len(results)}")

        if successful_processes:
            avg_quality = sum(r.get('quality_score', 0) for r in successful_processes) / len(successful_processes)
            print(f"   Average Quality Score: {avg_quality:.2f}/1.0")
            # Business readiness assessment
            print("\n🏢 Business Readiness:")
            print(f"   ✅ Automated Processing: {'✅' if avg_processing_time < 60 else '⚠️'}")
            print(f"   ✅ Cost Efficiency: {'✅' if total_cost < 1.0 else '⚠️'}")
            print(f"   ✅ Content Quality: {'✅' if avg_quality > 0.8 else '⚠️'}")
            print(f"   ✅ Scalability: {'✅' if len(successful_processes) == len(results) else '⚠️'}")

        return len(successful_processes) == len(results), f"Business workflow test: {len(successful_processes)}/{len(results)} successful"

    except Exception as e:
        print(f"❌ Business workflow test failed: {str(e)}")
        return False, str(e)

async def main():
    success, message = await test_business_video_processing()

    print("\n" + "=" * 60)
    print("🎯 BUSINESS WORKFLOW VERIFICATION RESULT:")
    if success:
        print("✅ BUSINESS WORKFLOW: PRODUCTION READY")
        print(f"Details: {message}")
    else:
        print("⚠️ BUSINESS WORKFLOW: NEEDS IMPROVEMENT")
        print(f"Issue: {message}")

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
