#!/usr/bin/env python3
"""
Real API Integration Verification Script
=======================================

Comprehensive testing and verification of real API integration replacing mock data.
Tests YouTube Data API, AI processing, cost monitoring, and error handling.
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Tuple

# REMOVED: sys.path manipulation - using proper relative imports instead

try:
    from ..services.real_youtube_api import RealYouTubeAPIService, get_youtube_service
    from ..services.real_ai_processor import RealAIProcessorService, get_ai_processor
    from ..services.real_video_processor import RealVideoProcessor, get_real_video_processor
    from ..services.api_cost_monitor import APICostMonitor, cost_monitor
except ImportError:
    try:
        from services.real_youtube_api import RealYouTubeAPIService, get_youtube_service
        from services.real_ai_processor import RealAIProcessorService, get_ai_processor
        from services.real_video_processor import RealVideoProcessor, get_real_video_processor
        from services.api_cost_monitor import APICostMonitor, cost_monitor
    except ImportError as e:
        print(f"❌ Failed to import real API services: {e}")
        print("Make sure you're running this script from the correct directory")
        sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

class RealAPIIntegrationVerifier:
    """
    Comprehensive verification of real API integration
    
    Tests:
    - Environment variable configuration
    - YouTube Data API connectivity and functionality
    - Multi-provider AI processing (OpenAI/Anthropic/Gemini)
    - Cost monitoring and tracking
    - Error handling and fallback mechanisms
    - Rate limiting and optimization
    """
    
    def __init__(self):
        self.test_results = []
        self.total_cost = 0.0
        self.start_time = datetime.now(timezone.utc)
        
        # Test video URLs (various types for comprehensive testing)
        self.test_videos = [
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo - compliance-safe
            "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo - first YouTube video
            "https://youtu.be/jNQXAC9IVRw",                 # Short URL format
        ]
        
        logger.info("🧪 Real API Integration Verifier initialized")
    
    def record_test_result(self, test_name: str, success: bool, details: Dict[str, Any], cost: float = 0.0):
        """Record test result"""
        result = {
            'test_name': test_name,
            'success': success,
            'details': details,
            'cost': cost,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.test_results.append(result)
        self.total_cost += cost
        
        status = "✅ PASS" if success else "❌ FAIL"
        cost_info = f" (${cost:.4f})" if cost > 0 else ""
        logger.info(f"{status} {test_name}{cost_info}")
        
        if details and not success:
            logger.error(f"   Details: {details}")
    
    async def test_environment_configuration(self) -> bool:
        """Test that all required environment variables are configured"""
        try:
            required_vars = {
                'YOUTUBE_API_KEY': 'YouTube Data API access',
                'OPENAI_API_KEY': 'OpenAI API access',
                'ANTHROPIC_API_KEY': 'Anthropic API access',
                'GEMINI_API_KEY': 'Google Gemini API access'
            }
            
            results = {}
            all_configured = True
            
            for var_name, description in required_vars.items():
                value = os.getenv(var_name)
                configured = bool(value and len(value) > 10)  # Basic validation
                results[var_name] = {
                    'configured': configured,
                    'description': description,
                    'length': len(value) if value else 0
                }
                if not configured:
                    all_configured = False
            
            # Optional but recommended variables
            optional_vars = {
                'API_COST_TRACKING': os.getenv('API_COST_TRACKING', 'true').lower() == 'true',
                'ENABLE_API_FALLBACKS': os.getenv('ENABLE_API_FALLBACKS', 'true').lower() == 'true',
                'FALLBACK_TO_CACHE': os.getenv('FALLBACK_TO_CACHE', 'true').lower() == 'true'
            }
            results['optional_config'] = optional_vars
            
            self.record_test_result(
                "Environment Configuration",
                all_configured,
                results
            )
            
            return all_configured
            
        except Exception as e:
            self.record_test_result(
                "Environment Configuration",
                False,
                {'error': str(e)}
            )
            return False
    
    async def test_youtube_api_service(self) -> bool:
        """Test YouTube Data API service functionality"""
        try:
            service = get_youtube_service()
            test_url = self.test_videos[0]
            
            # Test 1: Video ID extraction
            try:
                video_id = service.extract_video_id(test_url)
                id_extraction_success = len(video_id) == 11
            except Exception as e:
                id_extraction_success = False
                video_id = None
            
            # Test 2: Video metadata retrieval
            metadata_success = False
            metadata = None
            if video_id:
                try:
                    metadata = await service.get_video_metadata(video_id)
                    metadata_success = bool(metadata and metadata.title)
                except Exception as e:
                    logger.warning(f"Metadata retrieval failed: {e}")
            
            # Test 3: Transcript extraction
            transcript_success = False
            transcript_segments = 0
            if video_id:
                try:
                    transcript = await service.get_video_transcript(video_id)
                    transcript_success = True
                    transcript_segments = len(transcript)
                except Exception as e:
                    logger.warning(f"Transcript extraction failed: {e}")
            
            # Test 4: Comprehensive data retrieval
            comprehensive_success = False
            if video_id:
                try:
                    comprehensive_data = await service.get_comprehensive_video_data(test_url)
                    comprehensive_success = bool(
                        comprehensive_data.get('metadata') and
                        comprehensive_data.get('video_id') == video_id
                    )
                except Exception as e:
                    logger.warning(f"Comprehensive data retrieval failed: {e}")
            
            # Test 5: Video validation
            validation_success = False
            try:
                is_valid, vid, message = await service.validate_video_url(test_url)
                validation_success = is_valid and vid == video_id
            except Exception as e:
                logger.warning(f"Video validation failed: {e}")
            
            # Test 6: Search functionality
            search_success = False
            try:
                search_results = await service.search_videos("python tutorial", max_results=5)
                search_success = len(search_results) > 0
            except Exception as e:
                logger.warning(f"Search functionality failed: {e}")
            
            overall_success = all([
                id_extraction_success,
                metadata_success,
                comprehensive_success,
                validation_success
            ])
            
            test_details = {
                'video_id_extraction': id_extraction_success,
                'metadata_retrieval': metadata_success,
                'transcript_extraction': transcript_success,
                'transcript_segments': transcript_segments,
                'comprehensive_data': comprehensive_success,
                'video_validation': validation_success,
                'search_functionality': search_success,
                'test_video': test_url,
                'extracted_video_id': video_id,
                'video_title': metadata.title if metadata else None
            }
            
            self.record_test_result(
                "YouTube Data API Service",
                overall_success,
                test_details,
                cost=0.001  # Estimated API quota cost
            )
            
            return overall_success
            
        except Exception as e:
            self.record_test_result(
                "YouTube Data API Service",
                False,
                {'error': str(e)}
            )
            return False
    
    async def test_ai_processing_service(self) -> bool:
        """Test AI processing service with multiple providers"""
        try:
            processor = get_ai_processor()
            
            test_content = """
            This is a test video about machine learning fundamentals.
            The video covers linear regression, neural networks, and practical examples in Python.
            It's designed for beginners with 15 minutes of educational content.
            """
            
            # Test different AI providers and processing types
            test_cases = [
                ('openai', 'analysis'),
                ('anthropic', 'summary'),
                ('gemini', 'actions'),
                ('auto', 'categorization')
            ]
            
            results = {}
            total_test_cost = 0.0
            successful_tests = 0
            
            for provider, processing_type in test_cases:
                try:
                    from services.real_ai_processor import AIProcessingRequest, AIProvider, ProcessingType
                    
                    request = AIProcessingRequest(
                        content=test_content,
                        processing_type=ProcessingType(processing_type),
                        provider=AIProvider(provider),
                        video_id='test_video'
                    )
                    
                    result = await processor.process_content(request)
                    
                    test_success = result.success and bool(result.result)
                    if test_success:
                        successful_tests += 1
                    
                    total_test_cost += result.cost
                    
                    results[f"{provider}_{processing_type}"] = {
                        'success': test_success,
                        'provider_used': result.provider,
                        'model_used': result.model,
                        'tokens_used': result.tokens_used,
                        'cost': result.cost,
                        'processing_time': result.processing_time,
                        'has_result': bool(result.result),
                        'error': result.error_message if not result.success else None
                    }
                    
                except Exception as e:
                    results[f"{provider}_{processing_type}"] = {
                        'success': False,
                        'error': str(e)
                    }
            
            # Test comprehensive video analysis
            try:
                test_video_data = {
                    'video_id': 'test_video',
                    'metadata': {
                        'title': 'Test Video: Machine Learning Fundamentals',
                        'description': test_content,
                        'duration': 'PT15M',
                        'channel_title': 'Test Channel'
                    },
                    'transcript': {
                        'full_text': test_content,
                        'has_transcript': True,
                        'segment_count': 10
                    }
                }
                
                comprehensive_result = await processor.analyze_video_content(test_video_data)
                comprehensive_success = comprehensive_result.get('success', False)
                total_test_cost += comprehensive_result.get('total_cost', 0.0)
                
                results['comprehensive_analysis'] = {
                    'success': comprehensive_success,
                    'analyses_completed': sum(1 for k in ['content_analysis', 'summary', 'actions', 'categorization'] 
                                            if comprehensive_result.get(k) is not None),
                    'total_cost': comprehensive_result.get('total_cost', 0.0),
                    'providers_used': comprehensive_result.get('processing_providers', [])
                }
                
            except Exception as e:
                results['comprehensive_analysis'] = {
                    'success': False,
                    'error': str(e)
                }
            
            overall_success = successful_tests >= 2  # At least 2 out of 4 providers working
            
            self.record_test_result(
                "AI Processing Service",
                overall_success,
                {
                    'test_results': results,
                    'successful_providers': successful_tests,
                    'total_providers_tested': len(test_cases),
                    'available_providers': processor._get_available_providers()
                },
                cost=total_test_cost
            )
            
            return overall_success
            
        except Exception as e:
            self.record_test_result(
                "AI Processing Service",
                False,
                {'error': str(e)}
            )
            return False
    
    async def test_cost_monitoring_service(self) -> bool:
        """Test cost monitoring and tracking functionality"""
        try:
            monitor = cost_monitor
            
            # Test cost tracking
            try:
                # Record a test usage
                test_record = await monitor.record_usage(
                    service="openai",
                    endpoint="chat/completions",
                    tokens_used=100,
                    model="gpt-4o-mini",
                    output_tokens=50,
                    request_type="test",
                    video_id="test_video"
                )
                
                usage_recorded = test_record is not None
            except Exception as e:
                usage_recorded = False
                logger.warning(f"Usage recording failed: {e}")
            
            # Test analytics
            try:
                analytics = await monitor.get_usage_analytics(days=1)
                analytics_working = bool(analytics and 'service_breakdown' in analytics)
            except Exception as e:
                analytics_working = False
                logger.warning(f"Analytics failed: {e}")
            
            # Test cost dashboard
            try:
                dashboard = await monitor.get_cost_dashboard()
                dashboard_working = bool(dashboard and 'today_summary' in dashboard)
            except Exception as e:
                dashboard_working = False
                logger.warning(f"Dashboard failed: {e}")
            
            # Test optimization recommendations
            try:
                optimization = await monitor.optimize_api_usage()
                optimization_working = bool(optimization and 'recommendations' in optimization)
            except Exception as e:
                optimization_working = False
                logger.warning(f"Optimization failed: {e}")
            
            # Test rate limiting
            try:
                allowed, wait_time = monitor.check_rate_limit("openai")
                rate_limiting_working = isinstance(allowed, bool)
            except Exception as e:
                rate_limiting_working = False
                logger.warning(f"Rate limiting failed: {e}")
            
            overall_success = all([
                usage_recorded,
                analytics_working,
                dashboard_working,
                rate_limiting_working
            ])
            
            self.record_test_result(
                "Cost Monitoring Service",
                overall_success,
                {
                    'usage_recording': usage_recorded,
                    'analytics': analytics_working,
                    'dashboard': dashboard_working,
                    'optimization': optimization_working,
                    'rate_limiting': rate_limiting_working,
                    'cost_tracking_enabled': monitor.cost_tracking_enabled,
                    'daily_budget': monitor.daily_budget
                }
            )
            
            return overall_success
            
        except Exception as e:
            self.record_test_result(
                "Cost Monitoring Service",
                False,
                {'error': str(e)}
            )
            return False
    
    async def test_integrated_video_processor(self) -> bool:
        """Test the integrated real video processor"""
        try:
            processor = get_real_video_processor()
            test_url = self.test_videos[0]
            
            # Test video processing
            start_time = time.time()
            result = await processor.process_video(test_url)
            processing_time = time.time() - start_time
            
            success = result.get('success', False)
            video_id = result.get('video_id')
            has_metadata = bool(result.get('metadata'))
            has_transcript = result.get('transcript', {}).get('has_transcript', False)
            has_ai_analysis = result.get('ai_analysis', {}).get('success', False)
            processing_cost = result.get('cost_breakdown', {}).get('total_cost', 0.0)
            
            # Test validation
            validation_result = await processor.validate_and_process(test_url)
            validation_success = validation_result.get('valid', False)
            
            # Test status
            status = await processor.get_processing_status()
            status_success = status.get('service_status') == 'operational'
            
            overall_success = all([
                success,
                has_metadata,
                validation_success,
                status_success
            ])
            
            self.record_test_result(
                "Integrated Video Processor",
                overall_success,
                {
                    'processing_success': success,
                    'video_id': video_id,
                    'has_metadata': has_metadata,
                    'has_transcript': has_transcript,
                    'has_ai_analysis': has_ai_analysis,
                    'processing_time_seconds': round(processing_time, 2),
                    'validation_success': validation_success,
                    'service_status': status.get('service_status'),
                    'cached_videos': status.get('cache', {}).get('cached_videos', 0),
                    'error': result.get('error') if not success else None
                },
                cost=processing_cost
            )
            
            return overall_success
            
        except Exception as e:
            self.record_test_result(
                "Integrated Video Processor",
                False,
                {'error': str(e)}
            )
            return False
    
    async def test_error_handling_and_fallbacks(self) -> bool:
        """Test error handling and fallback mechanisms"""
        try:
            # Test invalid video URL
            processor = get_real_video_processor()
            
            invalid_urls = [
                "https://www.youtube.com/watch?v=invalidvideoid",
                "not_a_url_at_all",
                "https://www.youtube.com/watch?v=",
            ]
            
            error_handling_results = {}
            
            for i, invalid_url in enumerate(invalid_urls):
                try:
                    result = await processor.validate_and_process(invalid_url)
                    # Should return graceful error, not crash
                    handled_gracefully = not result.get('valid', True) and 'error' in result
                    error_handling_results[f'invalid_url_{i+1}'] = {
                        'handled_gracefully': handled_gracefully,
                        'error_message': result.get('error', 'No error message')
                    }
                except Exception as e:
                    # Should not raise unhandled exceptions
                    error_handling_results[f'invalid_url_{i+1}'] = {
                        'handled_gracefully': False,
                        'unhandled_exception': str(e)
                    }
            
            # Test API failure simulation (without valid keys)
            try:
                # Temporarily disable API key to test fallback
                original_key = os.getenv('YOUTUBE_API_KEY')
                os.environ['YOUTUBE_API_KEY'] = 'invalid_key_for_testing'
                
                # This should fail gracefully
                failed_result = await processor.process_video(self.test_videos[0])
                fallback_handled = not failed_result.get('success') and 'error' in failed_result
                
                # Restore original key
                if original_key:
                    os.environ['YOUTUBE_API_KEY'] = original_key
                
                error_handling_results['api_failure_fallback'] = {
                    'handled_gracefully': fallback_handled,
                    'error_message': failed_result.get('error', 'No error message')
                }
                
            except Exception as e:
                error_handling_results['api_failure_fallback'] = {
                    'handled_gracefully': False,
                    'unhandled_exception': str(e)
                }
            
            graceful_handling_count = sum(
                1 for result in error_handling_results.values() 
                if result.get('handled_gracefully', False)
            )
            
            overall_success = graceful_handling_count >= len(error_handling_results) * 0.8  # 80% success rate
            
            self.record_test_result(
                "Error Handling & Fallbacks",
                overall_success,
                {
                    'test_results': error_handling_results,
                    'graceful_handling_rate': f"{graceful_handling_count}/{len(error_handling_results)}",
                    'success_rate_percent': round((graceful_handling_count / len(error_handling_results)) * 100, 1)
                }
            )
            
            return overall_success
            
        except Exception as e:
            self.record_test_result(
                "Error Handling & Fallbacks",
                False,
                {'error': str(e)}
            )
            return False
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive final report"""
        total_time = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        successful_tests = sum(1 for result in self.test_results if result['success'])
        total_tests = len(self.test_results)
        success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        # Categorize results
        critical_tests = [
            "Environment Configuration",
            "YouTube Data API Service", 
            "AI Processing Service"
        ]
        
        critical_success = all(
            result['success'] for result in self.test_results 
            if result['test_name'] in critical_tests
        )
        
        report = {
            'verification_summary': {
                'overall_success': success_rate >= 80 and critical_success,
                'success_rate_percent': round(success_rate, 1),
                'successful_tests': successful_tests,
                'total_tests': total_tests,
                'critical_systems_operational': critical_success,
                'total_cost': round(self.total_cost, 4),
                'verification_time_seconds': round(total_time, 2)
            },
            'test_results': self.test_results,
            'recommendations': self._generate_recommendations(),
            'report_timestamp': datetime.now(timezone.utc).isoformat(),
            'system_status': 'OPERATIONAL' if (success_rate >= 80 and critical_success) else 'NEEDS_ATTENTION'
        }
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        for result in self.test_results:
            if not result['success']:
                test_name = result['test_name']
                details = result['details']
                
                if test_name == "Environment Configuration":
                    recommendations.append("Configure missing API keys in .env file")
                elif test_name == "YouTube Data API Service":
                    recommendations.append("Check YouTube API key validity and quota limits")
                elif test_name == "AI Processing Service":
                    if details.get('available_providers'):
                        recommendations.append(f"Only {len(details['available_providers'])} AI providers available - consider configuring more")
                    else:
                        recommendations.append("No AI providers configured - add OpenAI, Anthropic, or Gemini API keys")
                elif test_name == "Cost Monitoring Service":
                    recommendations.append("Cost monitoring service needs attention - check database permissions")
                elif test_name == "Error Handling & Fallbacks":
                    success_rate = float(details.get('success_rate_percent', 0))
                    if success_rate < 80:
                        recommendations.append("Improve error handling - some edge cases not handled gracefully")
        
        if self.total_cost > 1.0:
            recommendations.append(f"High testing cost (${self.total_cost:.4f}) - consider optimizing API usage")
        
        if not recommendations:
            recommendations.append("All systems operational - real API integration successful!")
        
        return recommendations
    
    async def run_full_verification(self) -> Dict[str, Any]:
        """Run complete verification suite"""
        logger.info("🚀 Starting Real API Integration Verification")
        logger.info("=" * 60)
        
        # Run all tests
        test_functions = [
            self.test_environment_configuration,
            self.test_youtube_api_service,
            self.test_ai_processing_service,
            self.test_cost_monitoring_service,
            self.test_integrated_video_processor,
            self.test_error_handling_and_fallbacks
        ]
        
        for test_func in test_functions:
            try:
                await test_func()
            except Exception as e:
                logger.error(f"Test function {test_func.__name__} failed: {e}")
                self.record_test_result(
                    test_func.__name__.replace('test_', '').replace('_', ' ').title(),
                    False,
                    {'error': f'Test function failed: {str(e)}'}
                )
        
        # Generate and return final report
        final_report = self.generate_final_report()
        
        logger.info("=" * 60)
        logger.info("🏁 Verification Complete")
        logger.info(f"Overall Success: {final_report['verification_summary']['overall_success']}")
        logger.info(f"Success Rate: {final_report['verification_summary']['success_rate_percent']}%")
        logger.info(f"Total Cost: ${final_report['verification_summary']['total_cost']}")
        logger.info(f"System Status: {final_report['system_status']}")
        
        if final_report['recommendations']:
            logger.info("\n📋 Recommendations:")
            for i, rec in enumerate(final_report['recommendations'], 1):
                logger.info(f"   {i}. {rec}")
        
        return final_report

async def main():
    """Main verification function"""
    try:
        verifier = RealAPIIntegrationVerifier()
        report = await verifier.run_full_verification()
        
        # Save report to file
        report_file = Path(__file__).parent.parent / "reports" / "real_api_verification_report.json"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📄 Full report saved to: {report_file}")
        
        # Return appropriate exit code
        if report['verification_summary']['overall_success']:
            logger.info("🎉 Real API Integration Verification PASSED")
            return 0
        else:
            logger.error("❌ Real API Integration Verification FAILED")
            return 1
            
    except Exception as e:
        logger.error(f"Verification failed with exception: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())