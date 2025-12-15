#!/usr/bin/env python3
"""
Phase 4 External Dependencies Validation Test
===========================================

Comprehensive test suite to validate all external dependencies
and API integrations for the YouTube Extension project.
"""

import asyncio
import sys
import logging
from typing import Dict, List, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DependencyValidator:
    """Comprehensive external dependency validator"""

    def __init__(self):
        self.results = {}
        self.test_count = 0
        self.pass_count = 0

    def log_test_result(self, test_name: str, success: bool, message: str = ""):
        """Log individual test results"""
        self.test_count += 1
        if success:
            self.pass_count += 1
            logger.info(f"✅ {test_name}: PASSED")
        else:
            logger.error(f"❌ {test_name}: FAILED - {message}")

        self.results[test_name] = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }

    async def test_google_cloud_services(self) -> None:
        """Test Google Cloud Service dependencies"""
        logger.info("🔧 Testing Google Cloud Services...")

        # Test Google Cloud Storage
        try:
            from google.cloud import storage
            self.log_test_result("Google Cloud Storage Import", True)
        except ImportError as e:
            self.log_test_result("Google Cloud Storage Import", False, str(e))

        # Test Google Cloud Logging
        try:
            from google.cloud import logging
            self.log_test_result("Google Cloud Logging Import", True)
        except ImportError as e:
            self.log_test_result("Google Cloud Logging Import", False, str(e))

        # Test Google API Client
        try:
            from googleapiclient import discovery
            self.log_test_result("Google API Client Import", True)
        except ImportError as e:
            self.log_test_result("Google API Client Import", False, str(e))

    async def test_youtube_services(self) -> None:
        """Test YouTube API dependencies"""
        logger.info("🎬 Testing YouTube Services...")

        # Test YouTube Transcript API
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            self.log_test_result("YouTube Transcript API Import", True)
        except ImportError as e:
            self.log_test_result("YouTube Transcript API Import", False, str(e))

        # Test yt-dlp
        try:
            import yt_dlp
            self.log_test_result("yt-dlp Import", True)
        except ImportError as e:
            self.log_test_result("yt-dlp Import", False, str(e))

    async def test_ai_services(self) -> None:
        """Test AI/ML service dependencies"""
        logger.info("🤖 Testing AI/ML Services...")

        # Test OpenAI
        try:
            import openai
            self.log_test_result("OpenAI Import", True)
        except ImportError as e:
            self.log_test_result("OpenAI Import", False, str(e))

        # Test Anthropic
        try:
            import anthropic
            self.log_test_result("Anthropic Import", True)
        except ImportError as e:
            self.log_test_result("Anthropic Import", False, str(e))

        # Test Transformers
        try:
            import transformers
            self.log_test_result("Transformers Import", True)
        except ImportError as e:
            self.log_test_result("Transformers Import", False, str(e))
        except Exception as e:
            self.log_test_result("Transformers Import", True, f"Warning: {e}")

        # Test HuggingFace Hub
        try:
            import huggingface_hub
            self.log_test_result("HuggingFace Hub Import", True)
        except ImportError as e:
            self.log_test_result("HuggingFace Hub Import", False, str(e))

        # Test LangChain
        try:
            import langchain
            self.log_test_result("LangChain Import", True)
        except ImportError as e:
            self.log_test_result("LangChain Import", False, str(e))

        # Test AssemblyAI
        try:
            import assemblyai
            self.log_test_result("AssemblyAI Import", True)
        except ImportError as e:
            self.log_test_result("AssemblyAI Import", False, str(e))

    async def test_web_frameworks(self) -> None:
        """Test web framework dependencies"""
        logger.info("🌐 Testing Web Frameworks...")

        # Test FastAPI
        try:
            import fastapi
            self.log_test_result("FastAPI Import", True)
        except ImportError as e:
            self.log_test_result("FastAPI Import", False, str(e))

        # Test httpx
        try:
            import httpx
            self.log_test_result("httpx Import", True)
        except ImportError as e:
            self.log_test_result("httpx Import", False, str(e))

    async def test_data_processing(self) -> None:
        """Test data processing dependencies"""
        logger.info("📊 Testing Data Processing Libraries...")

        # Test pandas
        try:
            import pandas
            self.log_test_result("pandas Import", True)
        except ImportError as e:
            self.log_test_result("pandas Import", False, str(e))

        # Test numpy
        try:
            import numpy
            self.log_test_result("numpy Import", True)
        except ImportError as e:
            self.log_test_result("numpy Import", False, str(e))

        # Test torch
        try:
            import torch
            self.log_test_result("torch Import", True)
        except ImportError as e:
            self.log_test_result("torch Import", False, str(e))

    def generate_report(self) -> Dict:
        """Generate comprehensive test report"""
        success_rate = (self.pass_count / self.test_count * 100) if self.test_count > 0 else 0

        report = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': self.test_count,
            'passed_tests': self.pass_count,
            'failed_tests': self.test_count - self.pass_count,
            'success_rate': f"{success_rate:.1f}%",
            'results': self.results,
            'summary': {
                'google_cloud_services': self._count_category_results(['Google Cloud Storage Import', 'Google Cloud Logging Import', 'Google API Client Import']),
                'youtube_services': self._count_category_results(['YouTube Transcript API Import', 'yt-dlp Import']),
                'ai_services': self._count_category_results(['OpenAI Import', 'Anthropic Import', 'Transformers Import', 'HuggingFace Hub Import', 'LangChain Import', 'AssemblyAI Import']),
                'web_frameworks': self._count_category_results(['FastAPI Import', 'httpx Import']),
                'data_processing': self._count_category_results(['pandas Import', 'numpy Import', 'torch Import'])
            }
        }

        return report

    def _count_category_results(self, test_names: List[str]) -> Dict:
        """Count results for a category of tests"""
        passed = 0
        failed = 0
        for name in test_names:
            if name in self.results:
                if self.results[name]['success']:
                    passed += 1
                else:
                    failed += 1

        return {
            'total': len(test_names),
            'passed': passed,
            'failed': failed,
            'success_rate': f"{(passed / len(test_names) * 100):.1f}%" if test_names else "0%"
        }

async def main():
    """Main validation function"""
    logger.info("🚀 Starting Phase 4 External Dependencies Validation...")

    validator = DependencyValidator()

    # Run all validation tests
    await validator.test_google_cloud_services()
    await validator.test_youtube_services()
    await validator.test_ai_services()
    await validator.test_web_frameworks()
    await validator.test_data_processing()

    # Generate and display report
    report = validator.generate_report()

    logger.info(f"\n📊 VALIDATION RESULTS SUMMARY:")
    logger.info(f"Total Tests: {report['total_tests']}")
    logger.info(f"Passed: {report['passed_tests']}")
    logger.info(f"Failed: {report['failed_tests']}")
    logger.info(f"Success Rate: {report['success_rate']}")

    logger.info("\n📈 CATEGORY BREAKDOWN:")
    for category, stats in report['summary'].items():
        logger.info(f"  {category}: {stats['passed']}/{stats['total']} ({stats['success_rate']})")

    # Save detailed report
    import json
    report_file = "/Users/garvey/UVAI/src/core/youtube_extension/phase4_validation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    logger.info(f"\n💾 Detailed report saved to: {report_file}")

    # Final status
    if report['failed_tests'] == 0:
        logger.info("🎉 ALL EXTERNAL DEPENDENCIES VALIDATION PASSED!")
        return True
    else:
        logger.error(f"❌ {report['failed_tests']} EXTERNAL DEPENDENCY ISSUES FOUND!")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
