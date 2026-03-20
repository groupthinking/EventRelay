#!/usr/bin/env python3
"""
COMPREHENSIVE TEST RUNNER
Runs the complete test suite for 100 Technical Business YouTube videos
with environment validation, error handling, and detailed reporting.
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path


class ComprehensiveTestRunner:
    """Comprehensive test runner for the YouTube video processing system"""

    def __init__(self):
        self.start_time = time.time()
        self.results = {}
        self.log_file = Path('comprehensive_test_results.log')

    async def run_environment_test(self):
        """Run environment setup test"""
        print("🔧 Running Environment Setup Test...")
        try:
            from test_environment_setup import main as env_test
            result = await env_test()
            self.results['environment_test'] = result
            return result
        except Exception as e:
            print(f"❌ Environment test failed: {e}")
            self.results['environment_test'] = False
            return False

    async def run_single_video_test(self):
        """Run a single video test to verify processing works"""
        print("\n🎯 Running Single Video Test...")
        try:
            from process_video_with_mcp import RealVideoProcessor

            processor = RealVideoProcessor(real_mode_only=True)
            test_video = "https://www.youtube.com/watch?v=8aGhZQkoFbQ"  # Event loop video

            print(f"   🎬 Testing with: {test_video}")
            result = await processor.process_video_real(test_video)

            if result and 'video_id' in result:
                print(f"   ✅ Single video test passed - Video ID: {result['video_id']}")
                self.results['single_video_test'] = True
                return True
            else:
                print("   ❌ Single video test failed - No valid result")
                self.results['single_video_test'] = False
                return False

        except Exception as e:
            print(f"   ❌ Single video test failed: {e}")
            self.results['single_video_test'] = False
            return False

    async def run_batch_test(self, max_videos=10):
        """Run a small batch test first"""
        print(f"\n📊 Running Batch Test (Limited to {max_videos} videos)...")
        try:
            from test_100_technical_videos import BatchVideoProcessor

            processor = BatchVideoProcessor()

            # Limit to first few videos for testing
            processor.technical_videos = processor.technical_videos[:max_videos]

            print(f"   📋 Testing with {len(processor.technical_videos)} videos")
            result = await processor.run_batch_test()

            if result and result['processed_count'] > 0:
                print(f"   ✅ Batch test passed - {result['processed_count']} videos processed")
                self.results['batch_test'] = True
                return True
            else:
                print("   ❌ Batch test failed - No videos processed")
                self.results['batch_test'] = False
                return False

        except Exception as e:
            print(f"   ❌ Batch test failed: {e}")
            self.results['batch_test'] = False
            return False

    async def run_full_test(self):
        """Run the complete 100 video test"""
        print("\n🚀 Running Full 100 Video Test...")
        try:
            from test_100_technical_videos import BatchVideoProcessor

            processor = BatchVideoProcessor()

            print(f"   📋 Testing with all {len(processor.technical_videos)} videos")
            result = await processor.run_batch_test()

            if result and result['processed_count'] > 0:
                print(f"   ✅ Full test completed - {result['processed_count']} videos processed")
                self.results['full_test'] = True
                return True
            else:
                print("   ❌ Full test failed - No videos processed")
                self.results['full_test'] = False
                return False

        except Exception as e:
            print(f"   ❌ Full test failed: {e}")
            self.results['full_test'] = False
            return False

    def generate_report(self):
        """Generate comprehensive test report"""
        total_time = time.time() - self.start_time

        report = {
            'test_summary': {
                'total_tests': len(self.results),
                'passed_tests': sum(1 for result in self.results.values() if result),
                'failed_tests': sum(1 for result in self.results.values() if not result),
                'total_time': total_time,
                'timestamp': datetime.now().isoformat()
            },
            'test_results': self.results,
            'recommendations': []
        }

        # Generate recommendations
        if not self.results.get('environment_test', False):
            report['recommendations'].append("Fix environment setup issues before proceeding")

        if not self.results.get('single_video_test', False):
            report['recommendations'].append("Check video processing dependencies and API keys")

        if not self.results.get('batch_test', False):
            report['recommendations'].append("Review batch processing logic and error handling")

        if not self.results.get('full_test', False):
            report['recommendations'].append("Consider running with fewer videos or check rate limits")

        # Save report
        report_file = Path('comprehensive_test_report.json')
        import json
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        # Print summary
        print("\n" + "="*60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("="*60)
        print(f"⏱️ Total Time: {total_time:.2f}s")
        print(f"📈 Tests Passed: {report['test_summary']['passed_tests']}/{report['test_summary']['total_tests']}")

        for test_name, result in self.results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {status} {test_name.replace('_', ' ').title()}")

        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"   • {rec}")

        print(f"\n📄 Detailed report saved to: {report_file}")
        print("="*60)

        return report

    async def run_all_tests(self, test_mode='full'):
        """Run all tests based on mode"""
        print("🎯 COMPREHENSIVE TEST RUNNER")
        print("="*60)
        print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎛️ Test Mode: {test_mode}")
        print("="*60)

        # Always run environment test first
        env_ok = await self.run_environment_test()
        if not env_ok:
            print("\n❌ Environment test failed. Stopping tests.")
            return False

        # Run single video test
        single_ok = await self.run_single_video_test()
        if not single_ok:
            print("\n❌ Single video test failed. Stopping tests.")
            return False

        # Run batch test
        batch_ok = await self.run_batch_test()
        if not batch_ok:
            print("\n❌ Batch test failed. Stopping tests.")
            return False

        # Run full test if requested
        if test_mode == 'full':
            full_ok = await self.run_full_test()
            self.results['full_test'] = full_ok

        # Generate report
        report = self.generate_report()

        return report['test_summary']['passed_tests'] == report['test_summary']['total_tests']

async def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description='Comprehensive Test Runner')
    parser.add_argument('--mode', choices=['quick', 'full'], default='quick',
                       help='Test mode: quick (10 videos) or full (100 videos)')
    parser.add_argument('--skip-env', action='store_true',
                       help='Skip environment test')

    args = parser.parse_args()

    runner = ComprehensiveTestRunner()

    try:
        success = await runner.run_all_tests(args.mode)

        if success:
            print("\n🎉 All tests completed successfully!")
            print("✅ The working version is ready for production use.")
        else:
            print("\n⚠️ Some tests failed. Please review the report and fix issues.")
            print("📄 Check the comprehensive_test_report.json for details.")

        return 0 if success else 1

    except KeyboardInterrupt:
        print("\n⏸️ Tests interrupted by user.")
        return 1

    except Exception as e:
        print(f"\n❌ Test runner failed with error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
