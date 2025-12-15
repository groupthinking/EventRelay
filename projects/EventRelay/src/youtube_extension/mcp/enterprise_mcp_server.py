#!/usr/bin/env python3
"""
Enterprise-Grade MCP Server with Circuit Breakers, Monitoring & Resilience
Integrates superior patterns from archived implementations for production reliability
"""

import asyncio
import json
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import traceback

# Enhanced imports for enterprise patterns
import psutil
from concurrent.futures import ThreadPoolExecutor
import aiohttp
import ssl
from collections import defaultdict, deque

# Import existing processors
# from video_extractor_enhanced import EnhancedVideoExtractor, VideoContent
# from notebooklm_processor import NotebookLMProcessor, VideoNotebook
# from videoprism_analyzer import VideoPrismAnalyzer, VideoPrismAnalysis

# MCP imports
try:
    from mcp import McpServer
    from mcp.types import (
        Tool, TextContent, CallToolResult, 
        GetPromptResult, Prompt, PromptMessage
    )
    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    logging.warning("MCP not available - running in standalone mode")

# Configure enterprise logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [ENTERPRISE-MCP] %(name)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('enterprise_mcp.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open" # Testing recovery

@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    max_timeout_seconds: int = 7200

@dataclass 
class MetricPoint:
    """Single metric data point"""
    timestamp: float
    value: float
    tags: Dict[str, str]

class CircuitBreaker:
    """Production-grade circuit breaker implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.timeout_start = 0
        self.call_count = 0
        self.success_calls = 0
        
        logger.info(f"🔌 Circuit breaker '{name}' initialized")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if not self._should_allow_request():
            raise CircuitBreakerOpenException(f"Circuit breaker '{self.name}' is OPEN")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if exc_type is None:
            await self._record_success()
        else:
            await self._record_failure(exc_val)
        return False
    
    def _should_allow_request(self) -> bool:
        """Check if request should be allowed"""
        now = time.time()
        
        if self.state == CircuitBreakerState.CLOSED:
            return True
        elif self.state == CircuitBreakerState.OPEN:
            if now - self.timeout_start >= self.config.timeout_seconds:
                self.state = CircuitBreakerState.HALF_OPEN
                self.success_count = 0
                logger.info(f"🔄 Circuit breaker '{self.name}' entering HALF_OPEN state")
                return True
            return False
        elif self.state == CircuitBreakerState.HALF_OPEN:
            return True
        
        return False
    
    async def _record_success(self):
        """Record successful operation"""
        self.call_count += 1
        self.success_calls += 1
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                logger.info(f"✅ Circuit breaker '{self.name}' recovered to CLOSED state")
        elif self.state == CircuitBreakerState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)
    
    async def _record_failure(self, exception):
        """Record failed operation"""
        self.call_count += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.OPEN
            self.timeout_start = time.time()
            logger.error(f"❌ Circuit breaker '{self.name}' back to OPEN state: {exception}")
        elif (self.state == CircuitBreakerState.CLOSED and 
              self.failure_count >= self.config.failure_threshold):
            self.state = CircuitBreakerState.OPEN
            self.timeout_start = time.time()
            logger.error(f"🚨 Circuit breaker '{self.name}' opened due to failures: {exception}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        success_rate = (self.success_calls / max(self.call_count, 1)) * 100
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_calls,
            "total_calls": self.call_count,
            "success_rate": round(success_rate, 2),
            "last_failure_time": self.last_failure_time,
            "timeout_remaining": max(0, self.config.timeout_seconds - (time.time() - self.timeout_start)) if self.state == CircuitBreakerState.OPEN else 0
        }

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class RateLimiter:
    """Token bucket rate limiter with burst support"""
    
    def __init__(self, rate: float, burst: int, name: str = "default"):
        self.rate = rate  # tokens per second
        self.burst = burst  # maximum tokens
        self.name = name
        self.tokens = burst
        self.last_update = time.time()
        
        logger.info(f"🚦 Rate limiter '{name}' initialized: {rate}/sec, burst {burst}")
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens from bucket"""
        now = time.time()
        
        # Add tokens based on elapsed time
        elapsed = now - self.last_update
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        
        logger.warning(f"🚫 Rate limit exceeded for '{self.name}'")
        return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get rate limiter metrics"""
        return {
            "name": self.name,
            "rate": self.rate,
            "burst": self.burst,
            "available_tokens": round(self.tokens, 2),
            "utilization": round((1 - self.tokens / self.burst) * 100, 2)
        }

class MetricsCollector:
    """Comprehensive metrics collection system"""
    
    def __init__(self, max_points: int = 10000):
        self.metrics = defaultdict(lambda: deque(maxlen=max_points))
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.start_time = time.time()
        
    def record_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None):
        """Record counter metric"""
        self.counters[name] += value
        self._record_metric(name, float(value), tags or {})
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record gauge metric"""
        self.gauges[name] = value
        self._record_metric(name, value, tags or {})
    
    def record_timing(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record timing metric"""
        self._record_metric(f"{name}.duration", duration, tags or {})
        
    def _record_metric(self, name: str, value: float, tags: Dict[str, str]):
        """Internal metric recording"""
        point = MetricPoint(
            timestamp=time.time(),
            value=value,
            tags=tags
        )
        self.metrics[name].append(point)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        now = time.time()
        uptime = now - self.start_time
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_metrics": len(self.metrics),
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "recent_activity": {
                name: len([p for p in points if now - p.timestamp < 300])  # Last 5 minutes
                for name, points in self.metrics.items()
            }
        }

class HealthChecker:
    """Comprehensive health monitoring system"""
    
    def __init__(self):
        self.checks = {}
        self.last_check_time = {}
        self.check_results = {}
        
    def register_check(self, name: str, check_fn: Callable, interval: int = 60):
        """Register health check"""
        self.checks[name] = {
            'function': check_fn,
            'interval': interval,
            'last_run': 0
        }
        logger.info(f"💊 Health check '{name}' registered")
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_status = "healthy"
        
        for name, config in self.checks.items():
            now = time.time()
            
            # Check if we need to run this check
            if now - config['last_run'] >= config['interval']:
                try:
                    result = await config['function']()
                    results[name] = {
                        "status": "healthy" if result.get("healthy", True) else "unhealthy",
                        "details": result,
                        "last_check": now
                    }
                    config['last_run'] = now
                    self.check_results[name] = results[name]
                    
                    if not result.get("healthy", True):
                        overall_status = "degraded"
                        
                except Exception as e:
                    results[name] = {
                        "status": "error",
                        "error": str(e),
                        "last_check": now
                    }
                    overall_status = "unhealthy"
                    logger.error(f"🚨 Health check '{name}' failed: {e}")
            else:
                # Use cached result
                results[name] = self.check_results.get(name, {"status": "pending"})
        
        return {
            "overall_status": overall_status,
            "checks": results,
            "timestamp": time.time()
        }

class RetryManager:
    """Intelligent retry manager with exponential backoff"""
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        
    async def execute_with_retry(self, operation: Callable, name: str = "operation") -> Any:
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"🔄 Executing {name}, attempt {attempt + 1}")
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt == self.max_attempts - 1:
                    logger.error(f"❌ {name} failed after {self.max_attempts} attempts: {e}")
                    break
                
                # Calculate exponential backoff delay
                delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                logger.warning(f"⏳ {name} attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
        
        raise last_exception

class EnterpriseMCPServer:
    """Enterprise-grade MCP server with reliability patterns"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        # Initialize enterprise components
        self.metrics = MetricsCollector()
        self.health_checker = HealthChecker()
        self.retry_manager = RetryManager()
        
        # Initialize circuit breakers
        self.circuit_breakers = {
            "youtube_api": CircuitBreaker("youtube_api"),
            "ai_processing": CircuitBreaker("ai_processing"), 
            "video_analysis": CircuitBreaker("video_analysis")
        }
        
        # Initialize rate limiters
        self.rate_limiters = {
            "api_calls": RateLimiter(rate=10.0, burst=50, name="api_calls"),
            "video_processing": RateLimiter(rate=2.0, burst=10, name="video_processing"),
            "ai_requests": RateLimiter(rate=5.0, burst=20, name="ai_requests")
        }
        
        # Initialize processors
        # self.video_extractor = EnhancedVideoExtractor(config)
        # self.notebook_processor = NotebookLMProcessor(config)
        # self.videoprism_analyzer = VideoPrismAnalyzer(config)
        
        # Initialize MCP server if available
        if HAS_MCP:
            self.server = McpServer("enterprise-video-processor")
            self._register_tools()
            self._register_health_checks()
        else:
            self.server = None
            logger.warning("MCP server not available - tools will run in standalone mode")
        
        # Processing cache with TTL
        self.processing_cache = {}
        self.cache_ttl = {}
        
        logger.info("🚀 Enterprise MCP Server initialized with full reliability stack")
    
    def _register_health_checks(self):
        """Register comprehensive health checks"""
        
        async def system_health():
            """System resource health check"""
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            healthy = (cpu_percent < 80 and 
                      memory.percent < 85 and
                      (disk.used / disk.total) < 0.9)
            
            return {
                "healthy": healthy,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": round((disk.used / disk.total) * 100, 2),
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        
        async def circuit_breaker_health():
            """Circuit breaker status health check"""
            all_healthy = all(cb.state == CircuitBreakerState.CLOSED 
                             for cb in self.circuit_breakers.values())
            
            return {
                "healthy": all_healthy,
                "circuit_breakers": {name: cb.get_metrics() 
                                   for name, cb in self.circuit_breakers.items()}
            }
        
        async def rate_limiter_health():
            """Rate limiter status health check"""
            return {
                "healthy": True,
                "rate_limiters": {name: rl.get_metrics() 
                                for name, rl in self.rate_limiters.items()}
            }
        
        async def cache_health():
            """Cache status health check"""
            now = time.time()
            active_cache_items = sum(1 for ttl in self.cache_ttl.values() if ttl > now)
            
            return {
                "healthy": True,
                "total_cached_items": len(self.processing_cache),
                "active_cached_items": active_cache_items,
                "cache_hit_rate": getattr(self, '_cache_hit_rate', 0)
            }
        
        self.health_checker.register_check("system", system_health, 30)
        self.health_checker.register_check("circuit_breakers", circuit_breaker_health, 60)
        self.health_checker.register_check("rate_limiters", rate_limiter_health, 60)
        self.health_checker.register_check("cache", cache_health, 120)
    
    def _register_tools(self):
        """Register tools with enterprise patterns"""
        if not self.server:
            return
        
        @self.server.call_tool()
        async def extract_video_content_enterprise(arguments: dict) -> CallToolResult:
            """Enterprise video extraction with full reliability stack"""
            
            operation_start = time.time()
            self.metrics.record_counter("video_extraction.requests")
            
            try:
                # Rate limiting
                if not await self.rate_limiters["video_processing"].acquire():
                    self.metrics.record_counter("video_extraction.rate_limited")
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps({
                            "error": "Rate limit exceeded",
                            "retry_after": 10
                        }))]
                    )
                
                video_url = arguments.get("video_url")
                languages = arguments.get("languages", ["en"])
                
                if not video_url:
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps({
                            "error": "video_url is required"
                        }))]
                    )
                
                # Check cache first
                cache_key = f"video_content_{hashlib.md5(video_url.encode()).hexdigest()}"
                if cache_key in self.processing_cache and self.cache_ttl.get(cache_key, 0) > time.time():
                    self.metrics.record_counter("video_extraction.cache_hit")
                    cached_result = self.processing_cache[cache_key]
                    cached_result["from_cache"] = True
                    return CallToolResult(
                        content=[TextContent(type="text", text=json.dumps(cached_result, indent=2))]
                    )
                
                self.metrics.record_counter("video_extraction.cache_miss")
                
                # Execute with circuit breaker and retry
                async def extract_operation():
                    async with self.circuit_breakers["video_analysis"]:
                        return await self.video_extractor.process_video(video_url, languages)
                
                video_content = await self.retry_manager.execute_with_retry(
                    extract_operation, 
                    "video_extraction"
                )
                
                # Create response
                response = {
                    "video_id": video_content.metadata.video_id,
                    "title": video_content.metadata.title,
                    "duration": video_content.metadata.duration,
                    "transcript_segments": len(video_content.transcript) if video_content.transcript else 0,
                    "summary": video_content.summary,
                    "key_points": video_content.key_points,
                    "topics": video_content.topics,
                    "processing_time": round(time.time() - operation_start, 2),
                    "from_cache": False,
                    "cache_key": cache_key
                }
                
                # Cache result
                self.processing_cache[cache_key] = response
                self.cache_ttl[cache_key] = time.time() + 3600  # 1 hour TTL
                
                # Record metrics
                self.metrics.record_timing("video_extraction.duration", time.time() - operation_start)
                self.metrics.record_counter("video_extraction.success")
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except CircuitBreakerOpenException as e:
                self.metrics.record_counter("video_extraction.circuit_breaker_open")
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "error": "Service temporarily unavailable",
                        "reason": "circuit_breaker_open",
                        "retry_after": 60
                    }))]
                )
            
            except Exception as e:
                self.metrics.record_counter("video_extraction.error")
                logger.error(f"Video extraction failed: {e}", exc_info=True)
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "error": str(e),
                        "processing_time": round(time.time() - operation_start, 2)
                    }))]
                )
        
        @self.server.call_tool()
        async def get_system_health(arguments: dict) -> CallToolResult:
            """Get comprehensive system health status"""
            
            try:
                health_status = await self.health_checker.run_checks()
                metrics_summary = self.metrics.get_summary()
                
                # Add circuit breaker status
                circuit_breaker_status = {
                    name: cb.get_metrics() 
                    for name, cb in self.circuit_breakers.items()
                }
                
                # Add rate limiter status
                rate_limiter_status = {
                    name: rl.get_metrics() 
                    for name, rl in self.rate_limiters.items()
                }
                
                response = {
                    "health": health_status,
                    "metrics": metrics_summary,
                    "circuit_breakers": circuit_breaker_status,
                    "rate_limiters": rate_limiter_status,
                    "cache_stats": {
                        "total_items": len(self.processing_cache),
                        "active_items": sum(1 for ttl in self.cache_ttl.values() if ttl > time.time())
                    },
                    "enterprise_features": {
                        "circuit_breakers": True,
                        "rate_limiting": True,
                        "health_monitoring": True,
                        "metrics_collection": True,
                        "retry_logic": True,
                        "intelligent_caching": True
                    }
                }
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(response, indent=2))]
                )
            
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "error": str(e),
                        "health": {"overall_status": "error"}
                    }))]
                )
        
        @self.server.call_tool()
        async def reset_circuit_breakers(arguments: dict) -> CallToolResult:
            """Reset all circuit breakers (admin operation)"""
            
            try:
                reset_breakers = arguments.get("breakers", list(self.circuit_breakers.keys()))
                reset_results = {}
                
                for breaker_name in reset_breakers:
                    if breaker_name in self.circuit_breakers:
                        cb = self.circuit_breakers[breaker_name]
                        cb.state = CircuitBreakerState.CLOSED
                        cb.failure_count = 0
                        cb.success_count = 0
                        reset_results[breaker_name] = "reset"
                        logger.info(f"🔄 Circuit breaker '{breaker_name}' reset")
                    else:
                        reset_results[breaker_name] = "not_found"
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "reset_results": reset_results,
                        "timestamp": time.time()
                    }, indent=2))]
                )
            
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps({
                        "error": str(e)
                    }))]
                )
        
        logger.info("🔧 All enterprise tools registered successfully")
    
    async def run_server(self):
        """Run the enterprise MCP server"""
        if not self.server:
            logger.error("MCP server not available")
            return
        
        logger.info("🚀 Starting Enterprise MCP Server with full reliability stack...")
        
        # Start background monitoring tasks
        asyncio.create_task(self._monitoring_loop())
        asyncio.create_task(self._cache_cleanup_loop())
        
        try:
            from mcp.server.stdio import stdio_server
            
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        except Exception as e:
            logger.error(f"Server failed to start: {e}")
            traceback.print_exc()
    
    async def _monitoring_loop(self):
        """Background monitoring and metrics collection"""
        while True:
            try:
                # Record system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                self.metrics.record_gauge("system.cpu_percent", cpu_percent)
                self.metrics.record_gauge("system.memory_percent", memory.percent)
                
                # Record circuit breaker metrics
                for name, cb in self.circuit_breakers.items():
                    cb_metrics = cb.get_metrics()
                    self.metrics.record_gauge(f"circuit_breaker.{name}.success_rate", cb_metrics["success_rate"])
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _cache_cleanup_loop(self):
        """Background cache cleanup"""
        while True:
            try:
                now = time.time()
                expired_keys = [
                    key for key, ttl in self.cache_ttl.items()
                    if ttl <= now
                ]
                
                for key in expired_keys:
                    self.processing_cache.pop(key, None)
                    self.cache_ttl.pop(key, None)
                
                if expired_keys:
                    logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
                    self.metrics.record_counter("cache.expired_items", len(expired_keys))
                
                await asyncio.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(600)

# Main execution
async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enterprise MCP Server for Video Processing")
    parser.add_argument("--mode", choices=["server", "health"], 
                       default="server", help="Operation mode")
    
    args = parser.parse_args()
    
    server = EnterpriseMCPServer()
    
    if args.mode == "server":
        await server.run_server()
    elif args.mode == "health":
        health_status = await server.health_checker.run_checks()
        print(json.dumps(health_status, indent=2))

if __name__ == "__main__":
    asyncio.run(main())