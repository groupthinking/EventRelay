#!/usr/bin/env python3
"""
Logging Service
===============

Enterprise-grade logging service with structured logging, error aggregation,
performance monitoring, and multi-output support for production environments.
"""

import asyncio
import json
import logging
import logging.handlers
import os
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
import aiohttp
import aiofiles
from pydantic import BaseModel

try:
    from backend.config.logging_config import get_logger, PerformanceLogger
except ImportError:
    # Fallback for direct imports
    from backend.config.logging_config import get_logger, PerformanceLogger


class LogLevel:
    """Standard log levels with numeric values"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class StructuredLogEntry(BaseModel):
    """Structured log entry model for consistent logging format"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    service_name: str = "youtube-extension-api"
    version: str = "2.0.0"
    environment: str = "production"
    
    # Request context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    # Performance metrics
    duration_ms: Optional[float] = None
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    # Error details
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    error_code: Optional[str] = None
    
    # API context
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    response_size: Optional[int] = None
    
    # Additional context
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class ErrorAggregator:
    """Aggregates and analyzes error patterns for monitoring"""
    
    def __init__(self, window_size: int = 3600):  # 1 hour window
        self.window_size = window_size
        self.error_buckets: Dict[str, List[Dict]] = {}
        self.last_cleanup = time.time()
    
    def add_error(self, error_signature: str, error_data: Dict):
        """Add error to aggregation buckets"""
        current_time = time.time()
        
        if error_signature not in self.error_buckets:
            self.error_buckets[error_signature] = []
        
        self.error_buckets[error_signature].append({
            'timestamp': current_time,
            'data': error_data
        })
        
        # Cleanup old entries
        if current_time - self.last_cleanup > 300:  # Every 5 minutes
            self._cleanup_old_errors()
            self.last_cleanup = current_time
    
    def _cleanup_old_errors(self):
        """Remove errors outside the window"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size
        
        for signature in list(self.error_buckets.keys()):
            self.error_buckets[signature] = [
                error for error in self.error_buckets[signature]
                if error['timestamp'] > cutoff_time
            ]
            
            # Remove empty buckets
            if not self.error_buckets[signature]:
                del self.error_buckets[signature]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get aggregated error summary"""
        current_time = time.time()
        summary = {
            'total_errors': 0,
            'error_rate_per_minute': 0,
            'top_errors': [],
            'error_trends': {}
        }
        
        all_errors = []
        for signature, errors in self.error_buckets.items():
            all_errors.extend(errors)
            summary['error_trends'][signature] = len(errors)
        
        summary['total_errors'] = len(all_errors)
        
        if all_errors:
            # Calculate error rate (errors per minute in last hour)
            recent_errors = [
                error for error in all_errors
                if current_time - error['timestamp'] < 3600
            ]
            summary['error_rate_per_minute'] = len(recent_errors) / 60
        
        # Get top error types
        error_counts = [(sig, len(errors)) for sig, errors in self.error_buckets.items()]
        summary['top_errors'] = sorted(error_counts, key=lambda x: x[1], reverse=True)[:10]
        
        return summary


class LoggingService:
    """
    Enterprise logging service with structured logging, aggregation, and monitoring
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = self._load_config(config)
        self.logger = get_logger(__name__)
        self.error_aggregator = ErrorAggregator()
        self.log_buffer: List[StructuredLogEntry] = []
        self.buffer_lock = asyncio.Lock()
        self.flush_task: Optional[asyncio.Task] = None
        self.metrics_cache: Dict[str, Any] = {}
        self.start_time = time.time()
        
        # Initialize logging outputs
        self._setup_outputs()
        
        # Start background tasks
        asyncio.create_task(self._start_periodic_flush())
    
    def _load_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Load logging configuration with defaults"""
        default_config = {
            'buffer_size': 100,
            'flush_interval': 30,  # seconds
            'max_log_file_size': 100 * 1024 * 1024,  # 100MB
            'log_retention_days': 30,
            'enable_remote_logging': os.getenv('ENABLE_REMOTE_LOGGING', 'false').lower() == 'true',
            'remote_endpoint': os.getenv('REMOTE_LOGGING_ENDPOINT', 'https://logs.uvai.com/api/ingest'),
            'log_directory': Path(os.getenv('LOG_DIRECTORY', 'logs')),
            'enable_performance_monitoring': True,
            'enable_error_aggregation': True
        }
        
        if config:
            default_config.update(config)
        
        return default_config
    
    def _setup_outputs(self):
        """Setup logging outputs (files, remote endpoints)"""
        log_dir = self.config['log_directory']
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup rotating file handlers
        self.structured_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'structured_logs.jsonl',
            maxBytes=self.config['max_log_file_size'],
            backupCount=5
        )
        
        self.error_handler = logging.handlers.RotatingFileHandler(
            log_dir / 'error_logs.jsonl',
            maxBytes=self.config['max_log_file_size'],
            backupCount=10
        )
    
    async def _start_periodic_flush(self):
        """Start periodic flushing of log buffer"""
        while True:
            try:
                await asyncio.sleep(self.config['flush_interval'])
                await self.flush_logs()
            except Exception as e:
                self.logger.error(f"Error in periodic flush: {e}")
    
    async def log_structured(
        self,
        level: Union[int, str],
        message: str,
        **kwargs
    ) -> None:
        """Log structured entry with full context"""
        
        # Convert level to string if numeric
        if isinstance(level, int):
            level_name = logging.getLevelName(level)
        else:
            level_name = level.upper()
        
        # Create structured log entry
        entry = StructuredLogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=level_name,
            logger_name=self.logger.name,
            message=message,
            environment=os.getenv('ENVIRONMENT', 'production'),
            **kwargs
        )
        
        # Add to buffer
        async with self.buffer_lock:
            self.log_buffer.append(entry)
            
            # Flush if buffer is full
            if len(self.log_buffer) >= self.config['buffer_size']:
                await self._flush_buffer()
    
    async def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """Log error with full context and return error ID"""
        
        error_id = f"ERR_{int(time.time() * 1000)}_{hash(str(error)) % 10000:04d}"
        
        error_data = {
            'error_type': error.__class__.__name__,
            'error_message': str(error),
            'stack_trace': traceback.format_exc(),
            'error_code': getattr(error, 'code', None),
            'correlation_id': error_id,
            **kwargs
        }
        
        if context:
            error_data['metadata'] = context
        
        await self.log_structured('ERROR', f"Error occurred: {str(error)}", **error_data)
        
        # Add to error aggregator
        if self.config['enable_error_aggregation']:
            error_signature = f"{error.__class__.__name__}:{hash(str(error)) % 1000}"
            self.error_aggregator.add_error(error_signature, error_data)
        
        return error_id
    
    async def log_api_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration_ms: float,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log API request with performance metrics"""
        
        level = 'INFO'
        if status_code >= 500:
            level = 'ERROR'
        elif status_code >= 400:
            level = 'WARNING'
        
        await self.log_structured(
            level,
            f"{method} {endpoint} - {status_code}",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            user_id=user_id,
            tags=['api-request', f'status-{status_code // 100}xx'],
            **kwargs
        )
    
    async def log_performance_metric(
        self,
        operation: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log performance metrics for monitoring"""
        
        await self.log_structured(
            'INFO',
            f"Performance: {operation} completed in {duration_ms:.2f}ms",
            operation=operation,
            duration_ms=duration_ms,
            tags=['performance', 'metrics'],
            metadata=metadata or {}
        )
    
    @contextmanager
    def performance_context(self, operation: str, **context):
        """Context manager for performance monitoring"""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            asyncio.create_task(self.log_performance_metric(operation, duration_ms, context))
    
    async def flush_logs(self) -> None:
        """Flush log buffer to outputs"""
        async with self.buffer_lock:
            if self.log_buffer:
                await self._flush_buffer()
    
    async def _flush_buffer(self) -> None:
        """Internal buffer flush implementation"""
        if not self.log_buffer:
            return
        
        logs_to_flush = self.log_buffer.copy()
        self.log_buffer.clear()
        
        try:
            # Write to files
            await self._write_to_files(logs_to_flush)
            
            # Send to remote endpoint
            if self.config['enable_remote_logging']:
                await self._send_to_remote(logs_to_flush)
                
        except Exception as e:
            self.logger.error(f"Failed to flush logs: {e}")
            # Re-add failed logs to buffer (with limit to prevent infinite growth)
            async with self.buffer_lock:
                self.log_buffer.extend(logs_to_flush[-50:])  # Keep last 50 failed logs
    
    async def _write_to_files(self, logs: List[StructuredLogEntry]) -> None:
        """Write logs to file outputs"""
        try:
            # Write structured logs
            structured_path = self.config['log_directory'] / 'structured_logs.jsonl'
            async with aiofiles.open(structured_path, 'a') as f:
                for log in logs:
                    await f.write(log.json() + '\n')
            
            # Write error logs separately
            error_logs = [log for log in logs if log.level in ['ERROR', 'CRITICAL']]
            if error_logs:
                error_path = self.config['log_directory'] / 'error_logs.jsonl'
                async with aiofiles.open(error_path, 'a') as f:
                    for log in error_logs:
                        await f.write(log.json() + '\n')
                        
        except Exception as e:
            self.logger.error(f"Failed to write logs to files: {e}")
    
    async def _send_to_remote(self, logs: List[StructuredLogEntry]) -> None:
        """Send logs to remote endpoint"""
        try:
            payload = {
                'logs': [log.dict() for log in logs],
                'source': 'youtube-extension-api',
                'version': '2.0.0',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config['remote_endpoint'],
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        self.logger.warning(f"Remote logging failed with status {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to send logs to remote: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get logging service health status"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        return {
            'status': 'healthy',
            'uptime_seconds': uptime,
            'buffer_size': len(self.log_buffer),
            'total_logs_processed': getattr(self, '_total_logs_processed', 0),
            'error_summary': self.error_aggregator.get_error_summary(),
            'last_flush': getattr(self, '_last_flush_time', None)
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            'logging_service': self.get_health_status(),
            'error_aggregation': self.error_aggregator.get_error_summary(),
            'performance_metrics': self.metrics_cache,
            'system_info': {
                'environment': os.getenv('ENVIRONMENT', 'unknown'),
                'log_level': os.getenv('LOG_LEVEL', 'INFO'),
                'remote_logging_enabled': self.config['enable_remote_logging']
            }
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources and flush remaining logs"""
        try:
            if self.flush_task:
                self.flush_task.cancel()
            
            await self.flush_logs()
            
        except Exception as e:
            self.logger.error(f"Error during logging service cleanup: {e}")


# Global logging service instance
_logging_service: Optional[LoggingService] = None


async def get_logging_service() -> LoggingService:
    """Get or create global logging service instance"""
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


async def log_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
    """Convenience function to log errors"""
    service = await get_logging_service()
    return await service.log_error(error, context)


async def log_api_request(method: str, endpoint: str, status_code: int, duration_ms: float, **kwargs) -> None:
    """Convenience function to log API requests"""
    service = await get_logging_service()
    await service.log_api_request(method, endpoint, status_code, duration_ms, **kwargs)


async def log_performance(operation: str, duration_ms: float, metadata: Optional[Dict[str, Any]] = None) -> None:
    """Convenience function to log performance metrics"""
    service = await get_logging_service()
    await service.log_performance_metric(operation, duration_ms, metadata)


def performance_monitor(operation: str, **context):
    """Decorator for performance monitoring"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            service = await get_logging_service()
            with service.performance_context(operation, **context):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                asyncio.create_task(log_performance(operation, duration_ms, context))
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                asyncio.create_task(log_error(e, {'operation': operation, 'duration_ms': duration_ms}))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator