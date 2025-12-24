#!/usr/bin/env python3
"""
Test Script for Real Video-to-Software Pipeline
===============================================

This script tests the complete real implementation of the UVAI video-to-software
pipeline to ensure all components work together correctly.
"""

import asyncio
import logging
import json
import sys
from pathlib import Path
from typing import Dict, Any
import tempfile
import shutil

# Add UVAI paths
uvai_root = Path(__file__).parent.parent.parent.parent
# REMOVED: sys.path.insert for uvai_root

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [TEST] %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineIntegrationTest:
    """
    Comprehensive test suite for the real video-to-software pipeline
    """
    
    def __init__(self):
        self.test_results = {}
        # Test cases with different YouTube video URLs
        self.test_videos = [
            {
                "url": "https://www.youtube.com/watch?v=aircAruvnKk",  # Educational video
                "expected_keywords": ["math", "fractal", "dimension"]
            },
            {
                "url": "https://www.youtube.com/watch?v=x7X9w_GIm1s",  # Music video
                "expected_keywords": ["music", "pop", "song"]
            },
            {
                "url": "https://www.youtube.com/watch?v=wXVvfFMTyzY",  # General content
                "expected_keywords": ["comedy", "entertainment", "vlog"]
            }
        ]
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests"""
        logger.info("🧪 Starting Real Pipeline Integration Tests")
        
        tests = [
            self.test_imports(),
            self.test_video_processor(),
            self.test_code_generator(),
            self.test_deployment_manager(),
            self.test_ai_insights(),
            self.test_end_to_end_pipeline()
        ]
        
        for test in tests:
            try:
                if asyncio.iscoroutine(test):
                    await test
                else:
                    test
            except Exception as e:
                logger.error(f"Test failed: {e}")
        
        return self.test_results
    
    def test_imports(self):
        """Test that all required modules can be imported"""
        logger.info("📦 Testing imports...")
        
        try:
            from real_video_processor import get_video_processor
            from code_generator import get_code_generator
            from deployment_manager import get_deployment_manager
            from ai_insights_processor import get_ai_insights
            
            self.test_results["imports"] = {
                "status": "success",
                "message": "All modules imported successfully"
            }
            logger.info("✅ Imports test passed")
            
        except Exception as e:
            self.test_results["imports"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Imports test failed: {e}")
    
    async def test_video_processor(self):
        """Test the real video processor"""
        logger.info("🎥 Testing video processor...")
        
        try:
            from real_video_processor import get_video_processor
            
            processor = get_video_processor()
            
            # Test with a simple video
            test_url = self.test_videos[0]["url"]
            result = await processor.process_video(test_url)
            
            # Validate result structure
            required_keys = ["status", "video_data", "processing_pipeline"]
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing required key: {key}")
            
            self.test_results["video_processor"] = {
                "status": "success",
                "message": "Video processor working correctly",
                "result_keys": list(result.keys())
            }
            logger.info("✅ Video processor test passed")
            
        except Exception as e:
            self.test_results["video_processor"] = {
                "status": "failed", 
                "error": str(e)
            }
            logger.error(f"❌ Video processor test failed: {e}")
    
    async def test_code_generator(self):
        """Test the code generator"""
        logger.info("🏗️ Testing code generator...")
        
        try:
            from code_generator import get_code_generator
            
            generator = get_code_generator()
            
            # Create test video analysis
            test_analysis = {
                "status": "success",
                "extracted_info": {
                    "title": "Test React Tutorial",
                    "technologies": ["react", "javascript"],
                    "features": ["responsive_design", "user_interface"],
                    "project_type": "web"
                }
            }
            
            test_config = {
                "type": "web",
                "features": ["responsive_design"],
                "title": "Test Project"
            }
            
            result = await generator.generate_project(test_analysis, test_config)
            
            # Validate result
            required_keys = ["framework", "files_created", "project_path"]
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing required key: {key}")
            
            # Check if files were actually created
            project_path = Path(result["project_path"])
            if not project_path.exists():
                raise ValueError("Project directory was not created")
            
            # Clean up
            if project_path.exists():
                shutil.rmtree(project_path)
            
            self.test_results["code_generator"] = {
                "status": "success",
                "message": "Code generator working correctly",
                "files_created": result.get("files_created", [])
            }
            logger.info("✅ Code generator test passed")
            
        except Exception as e:
            self.test_results["code_generator"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Code generator test failed: {e}")
    
    async def test_deployment_manager(self):
        """Test the deployment manager"""
        logger.info("🚀 Testing deployment manager...")
        
        try:
            from deployment_manager import get_deployment_manager
            
            manager = get_deployment_manager()
            
            # Create a temporary project for testing
            temp_dir = tempfile.mkdtemp(prefix="test_deploy_")
            temp_path = Path(temp_dir)
            
            # Create a simple test file
            (temp_path / "index.html").write_text("<html><body>Test</body></html>")
            
            test_config = {
                "title": "Test Deployment Project",
                "type": "web"
            }
            
            deployment_config = {
                "target": "vercel",
                "auto_deploy": True
            }
            
            result = await manager.deploy_project(str(temp_path), test_config, deployment_config)
            
            # Validate result structure
            required_keys = ["deployment_id", "timestamp", "deployments"]
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing required key: {key}")
            
            # Clean up
            shutil.rmtree(temp_path)
            
            self.test_results["deployment_manager"] = {
                "status": "success",
                "message": "Deployment manager working correctly",
                "deployments": list(result.get("deployments", {}).keys())
            }
            logger.info("✅ Deployment manager test passed")
            
        except Exception as e:
            self.test_results["deployment_manager"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ Deployment manager test failed: {e}")
    
    async def test_ai_insights(self):
        """Test AI insights processor"""
        logger.info("🧠 Testing AI insights processor...")
        
        try:
            from ai_insights_processor import get_ai_insights
            
            test_url = self.test_videos[0]["url"]
            result = await get_ai_insights(test_url)
            
            if result is None:
                raise ValueError("AI insights returned None")
            
            # Validate result structure
            required_keys = ["summary", "technologies_detected"]
            for key in required_keys:
                if key not in result:
                    raise ValueError(f"Missing required key: {key}")
            
            self.test_results["ai_insights"] = {
                "status": "success",
                "message": "AI insights processor working correctly",
                "service_used": result.get("service_used", "unknown")
            }
            logger.info("✅ AI insights test passed")
            
        except Exception as e:
            self.test_results["ai_insights"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ AI insights test failed: {e}")
    
    async def test_end_to_end_pipeline(self):
        """Test the complete end-to-end pipeline"""
        logger.info("🔄 Testing end-to-end pipeline...")
        
        try:
            from real_video_processor import get_video_processor
            from code_generator import get_code_generator
            from deployment_manager import get_deployment_manager
            
            # Step 1: Process video
            processor = get_video_processor()
            test_url = self.test_videos[0]["url"]
            video_analysis = await processor.process_video(test_url)
            
            if video_analysis.get("status") != "success":
                raise ValueError("Video processing failed in E2E test")
            
            # Step 2: Generate code
            generator = get_code_generator()
            project_config = {
                "type": "web",
                "features": ["responsive_design"],
                "title": "E2E Test Project"
            }
            generation_result = await generator.generate_project(video_analysis, project_config)
            
            # Step 3: Deploy (simulation)
            manager = get_deployment_manager()
            deployment_config = {"target": "vercel"}
            deployment_result = await manager.deploy_project(
                generation_result["project_path"],
                project_config,
                deployment_config
            )
            
            # Clean up
            project_path = Path(generation_result["project_path"])
            if project_path.exists():
                shutil.rmtree(project_path)
            
            self.test_results["end_to_end"] = {
                "status": "success",
                "message": "End-to-end pipeline working correctly",
                "pipeline_stages": [
                    "video_processing",
                    "code_generation", 
                    "deployment"
                ]
            }
            logger.info("✅ End-to-end test passed")
            
        except Exception as e:
            self.test_results["end_to_end"] = {
                "status": "failed",
                "error": str(e)
            }
            logger.error(f"❌ End-to-end test failed: {e}")
    
    def print_test_summary(self):
        """Print a summary of all test results"""
        logger.info("\n" + "="*60)
        logger.info("🧪 TEST SUMMARY")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result.get("status") == "success")
        failed_tests = total_tests - passed_tests
        
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {passed_tests}")
        logger.info(f"Failed: {failed_tests}")
        
        if failed_tests == 0:
            logger.info("🎉 ALL TESTS PASSED!")
        else:
            logger.warning(f"⚠️ {failed_tests} tests failed")
        
        # Print details for each test
        for test_name, result in self.test_results.items():
            status_emoji = "✅" if result.get("status") == "success" else "❌"
            logger.info(f"{status_emoji} {test_name}: {result.get('message', result.get('error', 'Unknown'))}")

async def main():
    """Main test function"""
    tester = PipelineIntegrationTest()
    
    try:
        logger.info("🚀 Starting Real Pipeline Integration Tests")
        await tester.run_all_tests()
        
        # Print summary
        tester.print_test_summary()
        
        # Save results to file
        results_file = Path(__file__).parent / "test_results.json"
        with open(results_file, "w") as f:
            json.dump(tester.test_results, f, indent=2)
        
        logger.info(f"📄 Test results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())