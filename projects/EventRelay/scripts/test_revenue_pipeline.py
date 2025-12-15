#!/usr/bin/env python3
"""
Test Revenue Pipeline: YouTube URL → Live Deployed Application
==============================================================

Tests the complete end-to-end monetizable product flow.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from youtube_extension.backend.revenue_pipeline import get_revenue_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_pipeline_without_deployment():
    """Test pipeline without deployment (faster for testing)"""
    logger.info("🧪 Testing Revenue Pipeline (no deployment)")
    logger.info("=" * 60)

    # Use a short, well-structured tech video for testing
    # This is a public video about Next.js
    test_video_url = "https://www.youtube.com/watch?v=Sklc_fQBmcs"  # Next.js tutorial (short)

    try:
        # Create pipeline without auto-deployment for faster testing
        pipeline = get_revenue_pipeline(auto_deploy=False)

        logger.info(f"\n📹 Processing video: {test_video_url}")
        logger.info("⏱️  This may take 30-60 seconds...\n")

        # Run the pipeline
        result = await pipeline.process_video_to_deployment(test_video_url)

        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("📊 PIPELINE TEST RESULTS")
        logger.info("=" * 60)

        if result['success']:
            logger.info("✅ Status: SUCCESS")
            logger.info(f"\n📺 Video: {result['video_title']}")
            logger.info(f"📁 Project: {result['project_path']}")
            logger.info(f"⏱️  Duration: {result['pipeline_duration_seconds']:.2f} seconds")

            logger.info("\n📦 Steps Completed:")
            for step, status in result['steps_completed'].items():
                icon = "✅" if status else "⏭️"
                logger.info(f"  {icon} {step.replace('_', ' ').title()}")

            logger.info("\n🔧 Metadata:")
            metadata = result['metadata']
            logger.info(f"  Video ID: {metadata['video_id']}")
            logger.info(f"  Channel: {metadata['channel']}")
            logger.info(f"  Files Generated: {metadata['files_generated']}")
            logger.info(f"  Architecture: {metadata['architecture']}")
            logger.info(f"  Framework: {metadata['framework']}")

            logger.info("\n🚀 Next Steps:")
            logger.info(f"  1. cd {result['project_path']}")
            logger.info("  2. npm install")
            logger.info("  3. npm run dev")
            logger.info("  4. vercel --prod  # To deploy")

            return True
        else:
            logger.error(f"❌ Status: FAILED")
            logger.error(f"Error: {result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False


async def test_pipeline_with_deployment():
    """Test complete pipeline including deployment (requires Vercel CLI and token)"""
    logger.info("🧪 Testing Complete Revenue Pipeline with Deployment")
    logger.info("=" * 60)
    logger.info("⚠️  This requires:")
    logger.info("  1. Vercel CLI installed (npm i -g vercel)")
    logger.info("  2. VERCEL_TOKEN environment variable set")
    logger.info("  3. May take 5-10 minutes to complete")
    logger.info("")

    # Ask for confirmation
    response = input("Continue with full deployment test? (y/N): ")
    if response.lower() != 'y':
        logger.info("Skipping deployment test")
        return False

    test_video_url = "https://www.youtube.com/watch?v=Sklc_fQBmcs"

    try:
        # Create pipeline WITH auto-deployment
        pipeline = get_revenue_pipeline(auto_deploy=True)

        logger.info(f"\n📹 Processing video: {test_video_url}")
        logger.info("⏱️  This will take several minutes...\n")

        # Run the complete pipeline
        result = await pipeline.process_video_to_deployment(test_video_url)

        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("📊 COMPLETE PIPELINE TEST RESULTS")
        logger.info("=" * 60)

        if result['success']:
            logger.info("✅ Status: SUCCESS")
            logger.info(f"\n📺 Video: {result['video_title']}")
            logger.info(f"📁 Project: {result['project_path']}")

            if result['deployment_url']:
                logger.info(f"🌐 LIVE AT: {result['deployment_url']}")
            else:
                logger.info("⚠️  Deployment was skipped or failed")

            logger.info(f"\n⏱️  Total Duration: {result['pipeline_duration_seconds']:.2f} seconds")

            logger.info("\n📦 Steps Completed:")
            for step, status in result['steps_completed'].items():
                icon = "✅" if status else "❌"
                logger.info(f"  {icon} {step.replace('_', ' ').title()}")

            return True
        else:
            logger.error(f"❌ Status: FAILED")
            logger.error(f"Error: {result.get('error')}")
            return False

    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}", exc_info=True)
        return False


async def main():
    """Main test runner"""
    logger.info("\n🚀 Revenue Pipeline Test Suite")
    logger.info("=" * 60)
    logger.info("Testing: YouTube URL → AI Code Generation → Deployment")
    logger.info("")

    # Test 1: Pipeline without deployment (faster)
    logger.info("\n【 Test 1: Pipeline without deployment 】")
    test1_success = await test_pipeline_without_deployment()

    if not test1_success:
        logger.error("\n❌ Test 1 failed. Fix issues before proceeding to deployment test.")
        sys.exit(1)

    logger.info("\n✅ Test 1 passed!")

    # Test 2: Complete pipeline with deployment (optional)
    logger.info("\n【 Test 2: Complete pipeline with deployment (optional) 】")
    test2_success = await test_pipeline_with_deployment()

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Test 1 (Generation): {'✅ PASSED' if test1_success else '❌ FAILED'}")
    logger.info(f"Test 2 (Deployment): {'✅ PASSED' if test2_success else '⏭️  SKIPPED'}")

    if test1_success:
        logger.info("\n🎉 Revenue pipeline is operational!")
        logger.info("Ready to convert YouTube videos to deployed applications.")
        return True
    else:
        logger.error("\n❌ Revenue pipeline has issues that need fixing.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
