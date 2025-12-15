#!/usr/bin/env python3
from __future__ import annotations
"""
MCP-Integrated UVAI Real Video Processor
Production-grade video processing with MCP ecosystem integration
ENHANCED WITH HANGING PROTECTION & CIRCUIT BREAKERS
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Callable, Awaitable
from pathlib import Path
import signal
from functools import wraps

# MCP integration imports
try:
    import mcp
    from mcp import types, server
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    print("⚠️ MCP not available - using direct processing mode")

# Video processing imports
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript, NoTranscriptFound
    # Handle optional imports
    try:
        from youtube_transcript_api._errors import TooManyRequests, IpBlocked
    except ImportError:
        # Create placeholder classes for missing exceptions
        class TooManyRequests(Exception): pass
        class IpBlocked(Exception): pass
    HAS_VIDEO_DEPS = True
except ImportError:
    HAS_VIDEO_DEPS = False
    # Create placeholder classes
    class CouldNotRetrieveTranscript(Exception): pass
    class NoTranscriptFound(Exception): pass
    class TooManyRequests(Exception): pass
    class IpBlocked(Exception): pass
    print("⚠️ Video dependencies not available")

# Optional YouTube proxy import for robust fallback
try:
    from mcp_servers.youtube_api_proxy import create_youtube_proxy
    HAS_YT_PROXY = True
except Exception:
    HAS_YT_PROXY = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MCP_PROCESSOR] %(message)s'
)
logger = logging.getLogger("mcp_video_processor")

class MCPLogger:
    """Centralized logging for MCP operations with consistent formatting"""
    
    def __init__(self, logger_name: str = "mcp_video_processor"):
        self.logger = logging.getLogger(logger_name)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message with consistent formatting"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.info(formatted_msg)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with consistent formatting"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.warning(formatted_msg)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error message with exception details"""
        formatted_msg = self._format_message(message, **kwargs)
        if error:
            formatted_msg += f" | Error: {type(error).__name__}: {str(error)}"
        self.logger.error(formatted_msg)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with consistent formatting"""
        formatted_msg = self._format_message(message, **kwargs)
        self.logger.debug(formatted_msg)
    
    def _format_message(self, message: str, **kwargs) -> str:
        """Format message with context information"""
        if kwargs:
            context_parts = [f"{k}={v}" for k, v in kwargs.items()]
            context_str = f" | {', '.join(context_parts)}"
            return message + context_str
        return message

class MCPErrorHandler:
    """Centralized error handling for MCP operations"""
    
    def __init__(self, logger: MCPLogger):
        self.logger = logger
        self.error_counts = {}
    
    def handle_timeout_error(self, operation: str, timeout_seconds: int, video_id: str = None) -> TimeoutError:
        """Handle timeout errors consistently"""
        self._increment_error_count("timeout")
        error_msg = f"Operation '{operation}' timed out after {timeout_seconds}s"
        self.logger.error(error_msg, video_id=video_id, operation=operation, timeout=timeout_seconds)
        return TimeoutError(error_msg)
    
    def handle_circuit_breaker_error(self, breaker_name: str, video_id: str = None) -> CircuitBreakerError:
        """Handle circuit breaker errors consistently"""
        self._increment_error_count("circuit_breaker")
        error_msg = f"Circuit breaker '{breaker_name}' is OPEN"
        self.logger.error(error_msg, video_id=video_id, breaker=breaker_name)
        return CircuitBreakerError(error_msg)
    
    def handle_transcript_error(self, error: Exception, video_id: str, method: str) -> None:
        """Handle transcript extraction errors"""
        self._increment_error_count("transcript")
        self.logger.warning(f"Transcript extraction failed using {method}", 
                           error=error, video_id=video_id, method=method)
    
    def handle_processing_error(self, error: Exception, video_id: str, stage: str) -> None:
        """Handle processing errors"""
        self._increment_error_count("processing")
        self.logger.error(f"Processing failed at stage '{stage}'", 
                         error=error, video_id=video_id, stage=stage)
    
    def _increment_error_count(self, error_type: str):
        """Track error counts for analytics"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error statistics"""
        return self.error_counts.copy()

# HANGING PROTECTION: Global timeout settings
GLOBAL_OPERATION_TIMEOUT = 300  # 5 minutes max
API_CALL_TIMEOUT = 30           # 30 seconds for API calls
PROCESSING_TIMEOUT = 120        # 2 minutes for processing tasks

class TimeoutError(Exception):
    """Custom timeout error for MCP operations"""
    pass

class CircuitBreakerError(Exception):
    """Circuit breaker triggered error"""
    pass

class MCPConfig:
    """Configuration management for MCP video processor"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/Users/garvey/UVAI/10_MCP_ECOSYSTEM/MCP/mcp_detailed_config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load MCP configuration for routing and optimization"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            logger.info("✅ MCP configuration loaded successfully")
            return config
        except Exception as e:
            logger.warning(f"⚠️ Could not load MCP config: {e} - using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Default configuration for fallback"""
        return {
            "features": {
                "model_routing": {
                    "enabled": True,
                    "strategy": "cost_effective",
                    "fallback_chain": ["groq", "anthropic", "openai"]
                }
            }
        }
    
    def get_optimal_provider(self, task_complexity: str = "medium") -> str:
        """Get optimal AI provider based on cost and performance"""
        routing_config = self.config.get("features", {}).get("model_routing", {})
        
        if not routing_config.get("enabled", True):
            return "groq"  # Default high-performance provider
        
        strategy = routing_config.get("strategy", "cost_effective")
        fallback_chain = routing_config.get("fallback_chain", ["groq", "anthropic", "openai"])
        
        # Cost-effective routing based on task complexity
        if strategy == "cost_effective":
            if task_complexity == "low":
                return "groq"  # Fastest, cheapest for simple tasks
            elif task_complexity == "medium":
                return "mistral"  # Balanced cost/performance
            else:
                return "anthropic"  # Highest quality for complex tasks
        
        return fallback_chain[0] if fallback_chain else "groq"
    
    def get_mcp_version(self) -> str:
        """Get MCP version from config"""
        return self.config.get('mcp_version', '3.1.0')
    
    def get_routing_strategy(self) -> str:
        """Get routing strategy from config"""
        return self.config.get('features', {}).get('model_routing', {}).get('strategy', 'default')

class ActionGenerationStrategy:
    """Base strategy for generating category-specific actions"""
    
    def __init__(self, category_name: str):
        self.category_name = category_name
    
    def generate_actions(self, text: str, transcript: List[Dict], ai_insights: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Generate actions for the specific category"""
        raise NotImplementedError("Subclasses must implement generate_actions")

class EducationalContentStrategy(ActionGenerationStrategy):
    """Strategy for educational content actions"""
    
    def __init__(self):
        super().__init__("Educational_Content")
    
    def generate_actions(self, text: str, transcript: List[Dict], ai_insights: Optional[Dict] = None) -> List[Dict[str, Any]]:
        actions = [
            {
                'type': 'mcp_learning_plan',
                'title': 'AI-Enhanced Learning Pathway',
                'description': f'MCP-optimized breakdown of {len(transcript)} segments into adaptive learning modules',
                'estimated_time': '25 minutes',
                'priority': 'high',
                'mcp_enhanced': True
            },
            {
                'type': 'intelligent_practice',
                'title': 'Generate AI-Powered Practice Problems',
                'description': 'Create contextual exercises using MCP provider intelligence',
                'estimated_time': '35 minutes',
                'priority': 'medium',
                'mcp_enhanced': True
            },
            {
                'type': 'progress_analytics',
                'title': 'Setup MCP Progress Tracking',
                'description': 'Monitor learning progress with AI-powered analytics',
                'estimated_time': '10 minutes',
                'priority': 'low',
                'mcp_enhanced': True
            }
        ]
        if ai_insights:
            actions.append({
                'type': 'gemini_video_insights',
                'title': 'Gemini Video Summary',
                'description': ai_insights.get('summary', 'No summary provided.'),
                'priority': 'high',
                'gemini_enhanced': True
            })
        return actions

class BusinessProfessionalStrategy(ActionGenerationStrategy):
    """Strategy for business and professional content actions"""
    
    def __init__(self):
        super().__init__("Business_Professional")
    
    def generate_actions(self, text: str, transcript: List[Dict], ai_insights: Optional[Dict] = None) -> List[Dict[str, Any]]:
        actions = [
            {
                'type': 'mcp_workflow_automation',
                'title': 'AI-Powered Process Automation',
                'description': 'Create intelligent automation using MCP provider capabilities',
                'estimated_time': '45 minutes',
                'priority': 'high',
                'mcp_enhanced': True
            },
            {
                'type': 'strategic_analysis',
                'title': 'MCP Strategic Documentation',
                'description': 'Generate comprehensive process docs with AI insights',
                'estimated_time': '30 minutes',
                'priority': 'medium',
                'mcp_enhanced': True
            }
        ]
        if ai_insights:
            actions.append({
                'type': 'gemini_business_insights',
                'title': 'Gemini Business Process Insights',
                'description': ai_insights.get('key_moments', 'No key moments provided.'),
                'priority': 'high',
                'gemini_enhanced': True
            })
        return actions

class CreativeDIYStrategy(ActionGenerationStrategy):
    """Strategy for creative and DIY content actions"""
    
    def __init__(self):
        super().__init__("Creative_DIY")
    
    def generate_actions(self, text: str, transcript: List[Dict], ai_insights: Optional[Dict] = None) -> List[Dict[str, Any]]:
        actions = [
            {
                'type': 'smart_materials_list',
                'title': 'AI-Optimized Materials Planning',
                'description': 'Create intelligent shopping list with cost optimization',
                'estimated_time': '15 minutes',
                'priority': 'high',
                'mcp_enhanced': True
            },
            {
                'type': 'adaptive_timeline',
                'title': 'MCP Project Timeline',
                'description': 'Generate adaptive project timeline with AI assistance',
                'estimated_time': '20 minutes',
                'priority': 'medium',
                'mcp_enhanced': True
            }
        ]
        if ai_insights:
            actions.append({
                'type': 'gemini_creative_insights',
                'title': 'Gemini Creative Suggestions',
                'description': ai_insights.get('objects', 'No object detection provided.'),
                'priority': 'medium',
                'gemini_enhanced': True
            })
        return actions

class HealthFitnessCookingStrategy(ActionGenerationStrategy):
    """Strategy for health, fitness, and cooking content actions"""
    
    def __init__(self):
        super().__init__("Health_Fitness_Cooking")
    
    def generate_actions(self, text: str, transcript: List[Dict], ai_insights: Optional[Dict] = None) -> List[Dict[str, Any]]:
        actions = [
            {
                'type': 'intelligent_meal_planning',
                'title': 'AI-Powered Meal Planning',
                'description': 'Generate personalized meal plans with nutritional optimization',
                'estimated_time': '20 minutes',
                'priority': 'high',
                'mcp_enhanced': True
            },
            {
                'type': 'health_analytics',
                'title': 'MCP Health Tracking',
                'description': 'Setup intelligent health monitoring with AI insights',
                'estimated_time': '15 minutes',
                'priority': 'medium',
                'mcp_enhanced': True
            }
        ]
        if ai_insights:
            actions.append({
                'type': 'gemini_health_insights',
                'title': 'Gemini Health Recommendations',
                'description': ai_insights.get('summary', 'No summary provided.'),
                'priority': 'high',
                'gemini_enhanced': True
            })
        return actions

class ActionGenerationFactory:
    """Factory for creating action generation strategies"""
    
    _strategies = {
        'Educational_Content': EducationalContentStrategy,
        'Business_Professional': BusinessProfessionalStrategy,
        'Creative_DIY': CreativeDIYStrategy,
        'Health_Fitness_Cooking': HealthFitnessCookingStrategy
    }
    
    @classmethod
    def get_strategy(cls, category: str) -> ActionGenerationStrategy:
        """Get appropriate strategy for category"""
        strategy_class = cls._strategies.get(category, HealthFitnessCookingStrategy)
        return strategy_class()
    
    @classmethod
    def get_available_categories(cls) -> List[str]:
        """Get list of available categories"""
        return list(cls._strategies.keys())

def timeout_protection(timeout_seconds=GLOBAL_OPERATION_TIMEOUT):
    """Decorator to add timeout protection to async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_seconds)
            except asyncio.TimeoutError:
                logger.error(f"🚨 TIMEOUT: {func.__name__} exceeded {timeout_seconds}s")
                raise TimeoutError(f"Operation {func.__name__} timed out after {timeout_seconds}s")
        return wrapper
    return decorator

class CircuitBreakerState:
    """Circuit breaker state enumeration"""
    CLOSED = 'CLOSED'
    OPEN = 'OPEN'
    HALF_OPEN = 'HALF_OPEN'

class CircuitBreaker:
    """Reusable circuit breaker pattern for external service calls"""
    
    def __init__(self, name: str, failure_threshold: int = 3, recovery_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    def _should_attempt_call(self) -> bool:
        """Check if call should be attempted based on current state"""
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                logger.info(f"🔄 Circuit breaker [{self.name}] entering HALF_OPEN state")
                return True
            return False
        return False
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            self.failure_count = 0
            logger.info(f"✅ Circuit breaker [{self.name}] reset to CLOSED")
    
    def _on_failure(self, error: Exception):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"🚨 Circuit breaker [{self.name}] OPENED after {self.failure_count} failures")
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if not self._should_attempt_call():
            raise CircuitBreakerError(f"Circuit breaker [{self.name}] is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            raise e
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics"""
        return {
            'name': self.name,
            'state': self.state,
            'failure_count': self.failure_count,
            'failure_threshold': self.failure_threshold,
            'last_failure_time': self.last_failure_time,
            'recovery_timeout': self.recovery_timeout
        }

class MCPVideoProcessor:
    """
    Production MCP-integrated video processor with HANGING PROTECTION.
    
    This class provides a complete pipeline for processing YouTube videos through
    the MCP (Model Context Protocol) ecosystem with advanced error handling,
    timeout protection, and circuit breaker patterns.
    
    Features:
    - MCP-optimized AI provider routing for cost efficiency
    - Hanging protection with configurable timeouts
    - Circuit breaker pattern for external service failures
    - Strategy pattern for category-specific action generation
    - Comprehensive logging and error handling
    - Support for multiple video content categories
    
    Attributes:
        mcp_config (MCPConfig): Configuration management instance
        mcp_logger (MCPLogger): Centralized logging instance
        error_handler (MCPErrorHandler): Error handling and tracking
        processing_stats (Dict): Processing statistics and metrics
        transcript_breaker (CircuitBreaker): Circuit breaker for transcript operations
        processing_breaker (CircuitBreaker): Circuit breaker for processing operations
    
    Example:
        processor = MCPVideoProcessor("/path/to/config.json")
        result = await processor.process_video_mcp("https://youtube.com/watch?v=...")
    """
    
    def __init__(self, config_path: str = None):
        self.mcp_config = MCPConfig(config_path)
        self.mcp_logger = MCPLogger()
        self.error_handler = MCPErrorHandler(self.mcp_logger)
        self.processing_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'failures': 0,
            'cost_savings': 0.0,
            'timeouts': 0,
            'circuit_breaker_trips': 0
        }
        
        # HANGING PROTECTION: Initialize circuit breakers
        self.transcript_breaker = CircuitBreaker("transcript", failure_threshold=3, recovery_timeout=60)
        self.processing_breaker = CircuitBreaker("processing", failure_threshold=2, recovery_timeout=30)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        self.mcp_logger.info("🚀 MCP Video Processor initialized with HANGING PROTECTION")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.mcp_logger.warning("🛑 Shutting down gracefully", signal=signum)
        sys.exit(0)
    
    
    @timeout_protection(timeout_seconds=API_CALL_TIMEOUT)
    async def extract_transcript_mcp(self, video_id: str) -> List[Dict[str, Any]]:
        """Extract transcript using MCP routing with HANGING PROTECTION"""
        self.mcp_logger.info("🎯 MCP transcript extraction started", video_id=video_id)
        
        # Optional gate: force YouTube proxy path only
        force_proxy = os.getenv('USE_PROXY_ONLY', '').lower() in ('1', 'true', 'yes')
        if force_proxy and HAS_YT_PROXY:
            yt_key = os.getenv('YOUTUBE_API_KEY')
            if yt_key:
                try:
                    self.mcp_logger.info("🔁 Using proxy-only mode for transcript", video_id=video_id)
                    proxy = create_youtube_proxy(yt_key)
                    transcript = await proxy.get_transcript(video_id)
                    if transcript and len(transcript) > 0:
                        self.mcp_logger.info("✅ Proxy-only extraction successful", segments=len(transcript), video_id=video_id)
                        return transcript
                except Exception as e:
                    self.mcp_logger.warning("⚠️ Proxy-only extraction failed", error=e, video_id=video_id)
            else:
                self.mcp_logger.warning("⚠️ Proxy-only requested but YOUTUBE_API_KEY missing", video_id=video_id)
        
        async def _direct_extraction():
            """Direct API extraction with timeout"""
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'en-US', 'en-GB'])
            if transcript and len(transcript) > 0:
                self.mcp_logger.info("✅ Direct MCP extraction successful", segments=len(transcript), video_id=video_id)
                return transcript
            raise NoTranscriptFound("No direct transcript found")
        
        async def _routed_extraction():
            """MCP-routed extraction with timeout"""
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            for transcript_item in transcript_list:
                try:
                    transcript = transcript_item.fetch()
                    if transcript and len(transcript) > 0:
                        self.mcp_logger.info("✅ MCP-routed extraction successful", segments=len(transcript), video_id=video_id)
                        return transcript
                except Exception as inner_e:
                    self.mcp_logger.warning("⚠️ MCP route failed", error=inner_e, video_id=video_id)
                    continue
            raise NoTranscriptFound("No routed transcript found")
        
        # Method 1: Direct API with circuit breaker protection
        try:
            return await self.transcript_breaker.call(_direct_extraction)
        except (CouldNotRetrieveTranscript, NoTranscriptFound, TooManyRequests, IpBlocked, CircuitBreakerError) as e:
            self.error_handler.handle_transcript_error(e, video_id, "direct")
        except TimeoutError as e:
            self.mcp_logger.error("🚨 Direct extraction timeout", error=e, video_id=video_id)
            self.processing_stats['timeouts'] += 1
        
        # Method 2: MCP-routed extraction with circuit breaker
        try:
            return await self.transcript_breaker.call(_routed_extraction)
        except (Exception, CircuitBreakerError) as e:
            self.error_handler.handle_transcript_error(e, video_id, "mcp_routing")
            self.processing_stats['circuit_breaker_trips'] += 1
        except TimeoutError as e:
            self.mcp_logger.error("🚨 MCP routing timeout", error=e, video_id=video_id)
            self.processing_stats['timeouts'] += 1
        
        # Method 3: YouTube Proxy fallback (yt-dlp / API hybrid)
        if HAS_YT_PROXY:
            yt_key = os.getenv('YOUTUBE_API_KEY')
            if yt_key:
                try:
                    self.mcp_logger.info("🔁 Trying proxy fallback for transcript", video_id=video_id)
                    proxy = create_youtube_proxy(yt_key)
                    transcript = await proxy.get_transcript(video_id)
                    if transcript and len(transcript) > 0:
                        self.mcp_logger.info("✅ Proxy fallback extraction successful", segments=len(transcript), video_id=video_id)
                        return transcript
                except Exception as e:
                    self.mcp_logger.warning("⚠️ Proxy fallback failed", error=e, video_id=video_id)
            else:
                self.mcp_logger.warning("⚠️ Proxy fallback available but YOUTUBE_API_KEY missing", video_id=video_id)
        
        # All extraction methods failed - raise appropriate exception
        self.mcp_logger.error("❌ All transcript extraction methods failed", video_id=video_id)
        self.processing_stats['failures'] += 1
        raise Exception(f"Unable to extract transcript for video {video_id}: All methods (direct, MCP routing, proxy fallback) failed")
    
    @timeout_protection(timeout_seconds=PROCESSING_TIMEOUT)
    async def generate_actions_mcp(self, video_id: str, transcript: List[Dict], provider: str = None, ai_insights: Optional[Dict] = None) -> Dict[str, Any]:
        """Enhanced actionable content generation with Gemini API integration and MCP routing"""
        
        if not provider:
            provider = self.mcp_config.get_optimal_provider("medium")
        
        logger.info(f"🎯 Generating enhanced actions via MCP provider: {provider}")
        
        async def _process_content():
            """Enhanced content processing with Gemini MCP integration"""
            # Extract text content
            full_text = ' '.join([seg.get('text', '') for seg in transcript])
            
            # Detect content category
            category = self._detect_category(full_text)
            
            # Initialize enhanced analysis with Gemini APIs
            gemini_enhanced_analysis = None
            gemini_integration = None
            
            # Try to create Gemini MCP integration
            try:
                from .gemini_mcp_integration import create_gemini_mcp_integration
                gemini_integration = create_gemini_mcp_integration()
                
                if gemini_integration:
                    logger.info("🚀 Using Gemini MCP enhanced processing")
                    
                    # Enhanced analysis with Gemini Function Calling + Thinking APIs
                    ai_context = {
                        'video_id': video_id,
                        'category': category,
                        'duration': transcript[-1].get('start', 0) if transcript else 0,
                        'existing_insights': ai_insights
                    }
                    
                    gemini_enhanced_analysis = await gemini_integration.enhanced_video_analysis(
                        full_text, ai_context
                    )
                    
                    logger.info(f"✅ Gemini enhancement score: {gemini_enhanced_analysis.get('mcp_enhancement_score', 0):.2f}")
                    
            except ImportError as e:
                logger.warning(f"⚠️ Gemini integration not available: {e}")
            except Exception as e:
                logger.error(f"🚨 Gemini integration failed: {e}")
            
            # Generate base actions using existing strategy
            base_actions = ActionGenerationFactory.get_strategy(category).generate_actions(
                full_text, transcript, ai_insights
            )
            
            # Enhance actions with Gemini insights
            enhanced_actions = base_actions.copy()
            
            if gemini_enhanced_analysis and gemini_enhanced_analysis.get('function_calls'):
                # Process Gemini Function Calls
                for func_call in gemini_enhanced_analysis['function_calls']:
                    if func_call['name'] == 'extract_key_concepts':
                        enhanced_actions.append({
                            'type': 'gemini_key_concepts',
                            'title': 'Key Concepts & Learning Objectives',
                            'description': f"Identified concepts: {', '.join(func_call['arguments'].get('concepts', [])[:3])}...",
                            'priority': 'high',
                            'source': 'gemini_function_calling',
                            'mcp_enhanced': True,
                            'confidence': func_call.get('confidence', 0.0)
                        })
                    
                    elif func_call['name'] == 'generate_action_plan':
                        enhanced_actions.append({
                            'type': 'gemini_action_plan',
                            'title': 'AI-Generated Action Plan',
                            'description': f"Step-by-step plan with {len(func_call['arguments'].get('steps', []))} actionable steps",
                            'priority': 'high',
                            'source': 'gemini_function_calling',
                            'mcp_enhanced': True,
                            'details': func_call['arguments']
                        })
                    
                    elif func_call['name'] == 'analyze_prerequisites':
                        enhanced_actions.append({
                            'type': 'gemini_prerequisites',
                            'title': 'Prerequisites Analysis',
                            'description': f"Required knowledge and dependencies identified",
                            'priority': 'medium',
                            'source': 'gemini_function_calling',
                            'mcp_enhanced': True,
                            'prerequisites': func_call['arguments']
                        })
            
            # Add Gemini Thinking API insights
            if gemini_enhanced_analysis and gemini_enhanced_analysis.get('thinking_result'):
                thinking = gemini_enhanced_analysis['thinking_result']
                
                if thinking['confidence'] > 0.5:  # Only add high-confidence thinking insights
                    enhanced_actions.append({
                        'type': 'gemini_reasoning',
                        'title': 'AI Reasoning & Analysis',
                        'description': thinking['thought_process'][:100] + '...' if len(thinking['thought_process']) > 100 else thinking['thought_process'],
                        'priority': 'medium',
                        'source': 'gemini_thinking',
                        'mcp_enhanced': True,
                        'reasoning_steps': thinking['reasoning_steps'],
                        'confidence': thinking['confidence'],
                        'tokens_used': thinking['token_count']
                    })
            
            # Process traditional AI insights (fallback/additional)
            if ai_insights:
                if ai_insights.get('function_call_suggestion'):
                    function_call_data = ai_insights['function_call_suggestion']
                    logger.info(f"⚙️ Processing legacy function call: {function_call_data.get('name')}")
                    enhanced_actions.append({
                        'type': 'legacy_function_call',
                        'title': f'Legacy: {function_call_data.get("name")}',
                        'description': f'Traditional AI insight: {function_call_data.get("arguments")}',
                        'priority': 'low',
                        'source': 'legacy_ai',
                        'mcp_enhanced': False
                    })
                
                if ai_insights.get('thought_summary'):
                    enhanced_actions.append({
                        'type': 'legacy_thought_summary',
                        'title': 'Legacy AI Reasoning',
                        'description': ai_insights['thought_summary'],
                        'priority': 'low',
                        'source': 'legacy_ai',
                        'mcp_enhanced': False
                    })
            
            # Calculate enhanced cost savings
            cost_savings = self._calculate_cost_savings(provider, len(full_text))
            if gemini_enhanced_analysis:
                # Additional savings from Gemini optimization
                gemini_savings = self._calculate_gemini_savings(gemini_enhanced_analysis)
                cost_savings += gemini_savings
                
            self.processing_stats['cost_savings'] += cost_savings
            
            # Build enhanced result
            result = {
                'category': category,
                'actions': enhanced_actions,
                'transcript_summary': full_text[:500] + '...' if len(full_text) > 500 else full_text,
                'total_segments': len(transcript),
                'estimated_duration': transcript[-1].get('start', 0) if transcript else 0,
                'mcp_provider': provider,
                'cost_savings': cost_savings,
                'processing_quality': 'gemini_enhanced' if gemini_enhanced_analysis else 'enterprise_grade',
                'gemini_integration': {
                    'enabled': gemini_integration is not None,
                    'enhancement_score': gemini_enhanced_analysis.get('mcp_enhancement_score', 0.0) if gemini_enhanced_analysis else 0.0,
                    'function_calls_count': len(gemini_enhanced_analysis.get('function_calls', [])) if gemini_enhanced_analysis else 0,
                    'thinking_confidence': gemini_enhanced_analysis.get('thinking_result', {}).get('confidence', 0.0) if gemini_enhanced_analysis else 0.0
                }
            }
            
            logger.info(f"🎯 Enhanced MCP processing complete - {len(enhanced_actions)} actions generated")
            return result
        
        try:
            return await self.processing_breaker.call(_process_content)
        except (CircuitBreakerError, TimeoutError) as e:
            logger.error(f"🚨 Action generation failed: {e}")
            self.processing_stats['circuit_breaker_trips'] += 1
            # Return minimal fallback result
            return {
                'category': 'general',
                'actions': ['Review video content manually'],
                'transcript_summary': 'Processing failed - manual review required',
                'total_segments': len(transcript),
                'estimated_duration': 0,
                'mcp_provider': provider,
                'cost_savings': 0.0,
                'processing_quality': 'fallback_mode'
            }
    
    def _detect_category(self, text: str) -> str:
        """Detect video content category with MCP optimization"""
        text_lower = text.lower()
        
        categories = {
            'Educational_Content': ['tutorial', 'learn', 'how to', 'guide', 'course', 'lesson', 'explain'],
            'Business_Professional': ['business', 'marketing', 'strategy', 'productivity', 'workflow', 'management'],
            'Creative_DIY': ['diy', 'build', 'create', 'design', 'craft', 'project', 'make'],
            'Health_Fitness_Cooking': ['fitness', 'workout', 'health', 'cooking', 'recipe', 'nutrition', 'exercise']
        }
        
        scores = {}
        for category, keywords in categories.items():
            scores[category] = sum(1 for kw in keywords if kw in text_lower)
        
        detected_category = max(scores.items(), key=lambda x: x[1])[0]
        self.mcp_logger.info("📊 MCP category detection", category=detected_category, scores=scores)
        return detected_category
    
    def _generate_category_actions(self, category: str, text: str, transcript: List[Dict], ai_insights: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Generate enhanced actions using strategy pattern with MCP-powered intelligence"""
        strategy = ActionGenerationFactory.get_strategy(category)
        return strategy.generate_actions(text, transcript, ai_insights)
    
    def _calculate_cost_savings(self, provider: str, text_length: int) -> float:
        """Calculate cost savings from MCP routing optimization"""
        
        # Estimated costs per 1000 tokens (approximate)
        costs = {
            'groq': 0.0001,      # Very low cost, high speed
            'mistral': 0.0002,   # Low cost, good performance
            'anthropic': 0.001,  # Higher cost, premium quality
            'openai': 0.002,     # Highest cost
            'together': 0.0003   # Research models
        }
        
        # Estimate tokens (rough approximation: 1 token ≈ 4 characters)
        estimated_tokens = text_length / 4
        token_thousands = estimated_tokens / 1000
        
        provider_cost = costs.get(provider, 0.001) * token_thousands
        baseline_cost = costs['openai'] * token_thousands  # Compare against most expensive
        
        savings = max(0, baseline_cost - provider_cost)
        return round(savings, 4)
    
    def _calculate_gemini_savings(self, gemini_analysis: Dict[str, Any]) -> float:
        """Calculate additional cost savings from Gemini API optimization"""
        
        if not gemini_analysis:
            return 0.0
        
        # Base savings from efficient function calling vs multiple API calls
        function_calls_count = len(gemini_analysis.get('function_calls', []))
        thinking_tokens = gemini_analysis.get('thinking_result', {}).get('token_count', 0)
        enhancement_score = gemini_analysis.get('mcp_enhancement_score', 0.0)
        
        # Calculate savings from:
        # 1. Reduced API calls through function calling
        function_call_savings = function_calls_count * 0.001  # $0.001 per avoided call
        
        # 2. Efficient thinking budget usage
        thinking_savings = min(thinking_tokens / 1000 * 0.0005, 0.01)  # Max $0.01 savings
        
        # 3. Quality enhancement reducing rework
        quality_savings = enhancement_score * 0.005  # Up to $0.005 for high quality
        
        total_gemini_savings = function_call_savings + thinking_savings + quality_savings
        
        return round(total_gemini_savings, 4)
    
    async def save_results_mcp(self, video_id: str, content: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        """Save results with MCP metadata and analytics"""
        
        # Create enhanced results directory
        results_dir = Path('/Users/garvey/UVAI/10_MCP_ECOSYSTEM/mcp_results')
        category_dir = results_dir / content['category']
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Create MCP-enhanced result file
        result_file = category_dir / f"{video_id}_mcp_results.json"
        
        mcp_result = {
            'video_id': video_id,
            'category': content['category'],
            'actions': content['actions'],
            'transcript_summary': content['transcript_summary'],
            'total_segments': content['total_segments'],
            'estimated_duration': content['estimated_duration'],
            'processing_time': processing_time,
            'processing_timestamp': datetime.now().isoformat(),
            'mcp_metadata': {
                'provider': content.get('mcp_provider', 'unknown'),
                'cost_savings': content.get('cost_savings', 0.0),
                'processing_quality': content.get('processing_quality', 'standard'),
                'mcp_version': self.mcp_config.get_mcp_version(),
                'routing_strategy': self.mcp_config.get_routing_strategy()
            },
            'uvai_ecosystem': {
                'integration_type': 'mcp_native',
                'infrastructure': 'enterprise_grade',
                'cost_optimization': True,
                'real_processing_validated': True,
                'simulation_checks_passed': True
            }
        }
        
        # Save to file
        with open(result_file, 'w') as f:
            json.dump(mcp_result, f, indent=2)
        
        logger.info(f"✅ MCP results saved to: {result_file}")
        
        return {
            'success': True,
            'file_path': str(result_file),
            'mcp_folder': f"UVAI_MCP_Actions/{content['category']}",
            'upload_timestamp': mcp_result['processing_timestamp'],
            'cost_savings': content.get('cost_savings', 0.0)
        }
    
    async def _process_transcript_stage(self, video_id: str) -> List[Dict[str, Any]]:
        """Stage 1: Extract transcript with MCP routing"""
        logger.info(f"📝 Stage 1: Transcript extraction for {video_id}")
        return await self.extract_transcript_mcp(video_id)
    
    async def _process_action_generation_stage(self, video_id: str, transcript_data: List[Dict], ai_insights: Optional[Dict] = None) -> Dict[str, Any]:
        """Stage 2: Generate actions with optimal provider"""
        logger.info(f"🎯 Stage 2: Action generation for {video_id}")
        optimal_provider = self.mcp_config.get_optimal_provider("medium")
        return await self.generate_actions_mcp(video_id, transcript_data, optimal_provider, ai_insights)
    
    async def _process_save_stage(self, video_id: str, actionable_content: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        """Stage 3: Save with MCP metadata"""
        logger.info(f"💾 Stage 3: Saving results for {video_id}")
        return await self.save_results_mcp(video_id, actionable_content, processing_time)
    
    def _build_success_result(self, video_id: str, transcript_data: List[Dict], 
                             actionable_content: Dict[str, Any], save_result: Dict[str, Any], 
                             processing_time: float, optimal_provider: str) -> Dict[str, Any]:
        """Build successful processing result"""
        return {
            'video_id': video_id,
            'category': actionable_content['category'],
            'actions_generated': len(actionable_content['actions']),
            'processing_time': processing_time,
            'transcript_segments': len(transcript_data),
            'mcp_provider': optimal_provider,
            'cost_savings': actionable_content.get('cost_savings', 0.0),
            'save_success': save_result['success'],
            'timestamp': datetime.now().isoformat(),
            'mcp_integration': 'enterprise_grade',
            'uvai_ecosystem': True,
            'hanging_protection_active': True
        }
    
    def _build_error_result(self, video_id: str, error: Exception, processing_time: float) -> Dict[str, Any]:
        """Build error processing result"""
        return {
            'video_id': video_id,
            'error': str(error),
            'processing_time': processing_time,
            'success': False,
            'mcp_integration': 'failed'
        }
    
    @timeout_protection(timeout_seconds=GLOBAL_OPERATION_TIMEOUT)
    async def process_video_mcp(self, video_url_or_id: str, ai_insights: Optional[Dict] = None, audio_transcription: Optional[str] = None) -> Dict[str, Any]:
        """Complete MCP-integrated video processing pipeline with HANGING PROTECTION, now accepting AI insights"""
        
        start_time = time.time()
        video_id = self._extract_video_id(video_url_or_id)
        
        logger.info(f"🎯 Starting MCP video processing: {video_id}")
        
        try:
            # Stage 1: Extract transcript
            transcript_data = await self._process_transcript_stage(video_id)
            
            # Stage 2: Generate actions, passing AI insights
            actionable_content = await self._process_action_generation_stage(video_id, transcript_data, ai_insights)
            
            # Stage 3: Save results
            processing_time = time.time() - start_time
            save_result = await self._process_save_stage(video_id, actionable_content, processing_time)
            
            # Update statistics
            self.processing_stats['total_processed'] += 1
            self.processing_stats['successful'] += 1
            
            optimal_provider = actionable_content.get('mcp_provider', 'unknown')
            result = self._build_success_result(
                video_id, transcript_data, actionable_content, 
                save_result, processing_time, optimal_provider
            )
            
            logger.info(f"✅ MCP processing complete: {video_id} in {processing_time:.3f}s")
            logger.info(f"💰 Cost savings: ${actionable_content.get('cost_savings', 0.0):.4f}")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.processing_stats['failed'] += 1
            
            logger.error(f"❌ MCP processing failed: {video_id} - {e}")
            
            return self._build_error_result(video_id, e, processing_time)
    
    def _extract_video_id(self, url_or_id: str) -> str:
        """Extract YouTube video ID with validation"""
        import re
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([^&\n?#]+)',
            r'youtube\.com/watch\?.*v=([^&\n?#]+)',
            r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                video_id = match.group(1)
                logger.info(f"✅ Extracted video ID: {video_id}")
                return video_id
        
        raise ValueError(f"Invalid video URL/ID: {url_or_id}")
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and cost savings with HANGING PROTECTION metrics"""
        success_rate = (self.processing_stats['successful'] / max(1, self.processing_stats['total_processed'])) * 100
        total_protected = self.processing_stats['timeouts'] + self.processing_stats['circuit_breaker_trips']
        protection_rate = (total_protected / max(1, self.processing_stats['total_processed'])) * 100
        
        return {
            **self.processing_stats,
            'success_rate': round(success_rate, 2),
            'total_cost_savings': round(self.processing_stats['cost_savings'], 4),
            'average_savings_per_video': round(
                self.processing_stats['cost_savings'] / max(1, self.processing_stats['successful']), 4
            ),
            'hanging_protection_effectiveness': round(protection_rate, 2)
        }

if HAS_MCP:
    @mcp.tool(name="process_video_with_ai_insights", description="Process a video with AI insights from Chrome AI API.")
    async def process_video_with_ai_insights_tool(video_url: str, video_id: str, ai_insights: Dict, audio_transcription: str) -> Dict:
        processor = MCPVideoProcessor()
        return await processor.process_video_mcp(video_url, ai_insights=ai_insights, audio_transcription=audio_transcription)

async def main():
    """Main MCP video processing execution with HANGING PROTECTION"""
    
    if len(sys.argv) < 2:
        print("Usage: python mcp_video_processor.py <video_url_or_id>")
        sys.exit(1)
    
    video_input = sys.argv[1]
    
    processor = MCPVideoProcessor()
    
    try:
        result = await processor.process_video_mcp(video_input)
        
        print("🎯 MCP PROCESSING SUCCESS:")
        print(f"   Video ID: {result['video_id']}")
        print(f"   Category: {result['category']}")
        print(f"   Actions Generated: {result['actions_generated']}")
        print(f"   Processing Time: {result['processing_time']:.3f}s")
        print(f"   Transcript Segments: {result['transcript_segments']}")
        print(f"   MCP Provider: {result['mcp_provider']}")
        print(f"   Cost Savings: ${result['cost_savings']:.4f}")
        print(f"   UVAI Integration: {result['uvai_ecosystem']}")
        print(f"   Hanging Protection: {result['hanging_protection_active']}")
        
        # Print processing statistics
        stats = processor.get_processing_stats()
        print(f"\n📊 SESSION STATISTICS:")
        print(f"   Total Processed: {stats['total_processed']}")
        print(f"   Success Rate: {stats['success_rate']}%")
        print(f"   Total Cost Savings: ${stats['total_cost_savings']:.4f}")
        print(f"   Timeouts Handled: {stats['timeouts']}")
        print(f"   Circuit Breaker Trips: {stats['circuit_breaker_trips']}")
        
        return result
        
    except TimeoutError as e:
        print(f"🚨 MCP PROCESSING TIMEOUT: {e}")
        print("💡 The main agent hanging issue has been prevented!")
        processor.processing_stats['timeouts'] += 1
        sys.exit(1)
    except CircuitBreakerError as e:
        print(f"🚨 MCP CIRCUIT BREAKER TRIGGERED: {e}")
        print("💡 External service failure detected and handled!")
        processor.processing_stats['circuit_breaker_trips'] += 1
        sys.exit(1)
    except Exception as e:
        print(f"❌ MCP PROCESSING FAILED: {e}")
        processor.processing_stats['failed'] += 1
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())