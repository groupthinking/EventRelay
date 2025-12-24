#!/usr/bin/env python3
"""
Error Handling Middleware
==========================

Enterprise-grade error handling middleware for FastAPI applications.
Provides comprehensive error catching, logging, monitoring, and user-friendly responses.
"""

import asyncio
import json
import time
import traceback
import uuid
from typing import Any, Dict, Optional, Union, Callable, Awaitable
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import psutil

from backend.services.logging_service import get_logging_service, log_error, log_api_request
from backend.config.logging_config import get_logger


class ErrorCategory:
    """Error categories for classification and handling"""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    INTERNAL_SERVER = "internal_server"
    EXTERNAL_SERVICE = "external_service"
    DATABASE = "database"
    NETWORK = "network"
    TIMEOUT = "timeout"


class ErrorResponse:
    """Standardized error response format"""
    
    def __init__(
        self,
        error_id: str,
        category: str,
        message: str,
        details: Optional[str] = None,
        user_message: Optional[str] = None,
        status_code: int = 500,
        retryable: bool = False,
        retry_after: Optional[int] = None
    ):
        self.error_id = error_id
        self.category = category
        self.message = message
        self.details = details
        self.user_message = user_message or self.get_user_friendly_message(category, status_code)
        self.status_code = status_code
        self.retryable = retryable
        self.retry_after = retry_after
    
    def get_user_friendly_message(self, category: str, status_code: int) -> str:
        """Generate user-friendly error messages"""
        messages = {
            ErrorCategory.VALIDATION: "Please check your input and try again.",
            ErrorCategory.AUTHENTICATION: "Please sign in to access this resource.",
            ErrorCategory.AUTHORIZATION: "You don't have permission to access this resource.",
            ErrorCategory.NOT_FOUND: "The requested resource could not be found.",
            ErrorCategory.RATE_LIMIT: "Too many requests. Please try again later.",
            ErrorCategory.INTERNAL_SERVER: "We're experiencing technical difficulties. Please try again later.",
            ErrorCategory.EXTERNAL_SERVICE: "We're having trouble connecting to external services. Please try again later.",
            ErrorCategory.DATABASE: "We're experiencing database issues. Please try again later.",
            ErrorCategory.NETWORK: "Network connectivity issues. Please check your connection and try again.",
            ErrorCategory.TIMEOUT: "The request took too long to process. Please try again."
        }
        
        return messages.get(category, "An unexpected error occurred. Please try again later.")
    
    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        response = {
            "error": {
                "id": self.error_id,
                "category": self.category,
                "message": self.user_message,
                "retryable": self.retryable,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }
        
        if self.retry_after:
            response["error"]["retry_after"] = self.retry_after
        
        if include_details and self.details:
            response["error"]["details"] = self.details
            response["error"]["technical_message"] = self.message
        
        return response


class ErrorClassifier:
    """Classifies errors into categories and determines appropriate responses"""
    
    @staticmethod
    def classify_exception(exception: Exception, status_code: Optional[int] = None) -> ErrorResponse:
        """Classify exception and return appropriate error response"""
        
        error_id = f"ERR_{uuid.uuid4().hex[:8].upper()}"
        
        # HTTP Exceptions
        if isinstance(exception, (HTTPException, StarletteHTTPException)):
            return ErrorClassifier._classify_http_exception(exception, error_id)
        
        # Validation Errors
        if isinstance(exception, RequestValidationError):
            return ErrorClassifier._classify_validation_error(exception, error_id)
        
        # Database Errors
        if ErrorClassifier._is_database_error(exception):
            return ErrorClassifier._classify_database_error(exception, error_id)
        
        # Network/External Service Errors
        if ErrorClassifier._is_network_error(exception):
            return ErrorClassifier._classify_network_error(exception, error_id)
        
        # Timeout Errors
        if ErrorClassifier._is_timeout_error(exception):
            return ErrorClassifier._classify_timeout_error(exception, error_id)
        
        # Generic Internal Server Error
        return ErrorResponse(
            error_id=error_id,
            category=ErrorCategory.INTERNAL_SERVER,
            message=str(exception),
            status_code=500,
            retryable=True
        )
    
    @staticmethod
    def _classify_http_exception(exception: Union[HTTPException, StarletteHTTPException], error_id: str) -> ErrorResponse:
        """Classify HTTP exceptions"""
        status_code = exception.status_code
        detail = exception.detail if hasattr(exception, 'detail') else str(exception)
        
        category_map = {
            400: ErrorCategory.VALIDATION,
            401: ErrorCategory.AUTHENTICATION,
            403: ErrorCategory.AUTHORIZATION,
            404: ErrorCategory.NOT_FOUND,
            429: ErrorCategory.RATE_LIMIT,
        }
        
        category = category_map.get(status_code, ErrorCategory.INTERNAL_SERVER)
        retryable = status_code in [429, 500, 502, 503, 504]
        retry_after = 60 if status_code == 429 else None
        
        return ErrorResponse(
            error_id=error_id,
            category=category,
            message=detail,
            status_code=status_code,
            retryable=retryable,
            retry_after=retry_after
        )
    
    @staticmethod
    def _classify_validation_error(exception: RequestValidationError, error_id: str) -> ErrorResponse:
        """Classify validation errors"""
        errors = []
        for error in exception.errors():
            field = " -> ".join(str(x) for x in error["loc"])
            message = error["msg"]
            errors.append(f"{field}: {message}")
        
        details = "; ".join(errors)
        
        return ErrorResponse(
            error_id=error_id,
            category=ErrorCategory.VALIDATION,
            message=f"Validation error: {details}",
            details=details,
            status_code=422,
            retryable=False
        )
    
    @staticmethod
    def _is_database_error(exception: Exception) -> bool:
        """Check if exception is database-related"""
        db_error_patterns = [
            'connection', 'database', 'sql', 'query', 'transaction',
            'deadlock', 'timeout', 'constraint', 'integrity'
        ]
        
        error_str = str(exception).lower()
        return any(pattern in error_str for pattern in db_error_patterns)
    
    @staticmethod
    def _classify_database_error(exception: Exception, error_id: str) -> ErrorResponse:
        """Classify database errors"""
        return ErrorResponse(
            error_id=error_id,
            category=ErrorCategory.DATABASE,
            message=f"Database error: {str(exception)}",
            status_code=503,
            retryable=True,
            retry_after=30
        )
    
    @staticmethod
    def _is_network_error(exception: Exception) -> bool:
        """Check if exception is network-related"""
        network_patterns = [
            'connection', 'network', 'timeout', 'dns', 'socket',
            'unreachable', 'refused', 'reset', 'http'
        ]
        
        error_str = str(exception).lower()
        return any(pattern in error_str for pattern in network_patterns)
    
    @staticmethod
    def _classify_network_error(exception: Exception, error_id: str) -> ErrorResponse:
        """Classify network errors"""
        return ErrorResponse(
            error_id=error_id,
            category=ErrorCategory.NETWORK,
            message=f"Network error: {str(exception)}",
            status_code=502,
            retryable=True,
            retry_after=60
        )
    
    @staticmethod
    def _is_timeout_error(exception: Exception) -> bool:
        """Check if exception is timeout-related"""
        timeout_patterns = ['timeout', 'time out', 'timed out', 'deadline exceeded']
        error_str = str(exception).lower()
        return any(pattern in error_str for pattern in timeout_patterns)
    
    @staticmethod
    def _classify_timeout_error(exception: Exception, error_id: str) -> ErrorResponse:
        """Classify timeout errors"""
        return ErrorResponse(
            error_id=error_id,
            category=ErrorCategory.TIMEOUT,
            message=f"Timeout error: {str(exception)}",
            status_code=504,
            retryable=True,
            retry_after=120
        )


class RequestTracker:
    """Tracks request context and performance metrics"""
    
    def __init__(self):
        self.active_requests: Dict[str, Dict[str, Any]] = {}
    
    def start_request(self, request_id: str, request: Request) -> Dict[str, Any]:
        """Start tracking a request"""
        context = {
            'request_id': request_id,
            'method': request.method,
            'url': str(request.url),
            'client_ip': self.get_client_ip(request),
            'user_agent': request.headers.get('user-agent', ''),
            'start_time': time.time(),
            'memory_start': self.get_memory_usage(),
            'headers': dict(request.headers)
        }
        
        self.active_requests[request_id] = context
        return context
    
    def end_request(self, request_id: str, status_code: int) -> Dict[str, Any]:
        """End request tracking and return metrics"""
        if request_id not in self.active_requests:
            return {}
        
        context = self.active_requests.pop(request_id)
        end_time = time.time()
        
        context.update({
            'end_time': end_time,
            'duration_ms': (end_time - context['start_time']) * 1000,
            'memory_end': self.get_memory_usage(),
            'status_code': status_code
        })
        
        context['memory_used'] = context['memory_end'] - context['memory_start']
        
        return context
    
    def get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip
        
        # Fallback to client IP
        if hasattr(request, 'client') and request.client:
            return request.client.host
        
        return 'unknown'
    
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive error handling middleware for FastAPI applications
    """
    
    def __init__(
        self,
        app: ASGIApp,
        debug: bool = False,
        enable_request_tracking: bool = True,
        enable_performance_monitoring: bool = True,
        max_request_size: int = 10 * 1024 * 1024,  # 10MB
        timeout_seconds: float = 7200.0  # 5 minutes
    ):
        super().__init__(app)
        self.debug = debug
        self.enable_request_tracking = enable_request_tracking
        self.enable_performance_monitoring = enable_performance_monitoring
        self.max_request_size = max_request_size
        self.timeout_seconds = timeout_seconds
        self.logger = get_logger(__name__)
        self.request_tracker = RequestTracker() if enable_request_tracking else None
        
        # Error rate tracking
        self.error_counts: Dict[str, int] = {}
        self.last_error_reset = time.time()
        
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Main middleware dispatch method"""
        
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start request tracking
        if self.request_tracker:
            context = self.request_tracker.start_request(request_id, request)
        else:
            context = {'request_id': request_id}
        
        try:
            # Check request size
            if hasattr(request, 'headers') and 'content-length' in request.headers:
                content_length = int(request.headers['content-length'])
                if content_length > self.max_request_size:
                    raise HTTPException(413, "Request too large")
            
            # Process request with timeout
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout_seconds
            )
            
            # Log successful request
            if self.enable_performance_monitoring:
                if self.request_tracker:
                    metrics = self.request_tracker.end_request(request_id, response.status_code)
                    await log_api_request(
                        method=context.get('method', 'UNKNOWN'),
                        endpoint=context.get('url', 'unknown'),
                        status_code=response.status_code,
                        duration_ms=metrics.get('duration_ms', 0),
                        request_id=request_id,
                        client_ip=context.get('client_ip'),
                        memory_used=metrics.get('memory_used', 0)
                    )
            
            return response
            
        except asyncio.TimeoutError:
            return await self.handle_timeout_error(request, context)
        
        except Exception as exception:
            return await self.handle_exception(request, exception, context)
    
    async def handle_exception(self, request: Request, exception: Exception, context: Dict[str, Any]) -> JSONResponse:
        """Handle exceptions with comprehensive error processing"""
        
        try:
            # Classify the error
            error_response = ErrorClassifier.classify_exception(exception)
            
            # Log the error with full context
            error_id = await log_error(
                exception,
                context={
                    **context,
                    'error_id': error_response.error_id,
                    'error_category': error_response.category,
                    'stack_trace': traceback.format_exc()
                }
            )
            
            # Update error tracking
            self.update_error_tracking(error_response.category)
            
            # Create response
            response_data = error_response.to_dict(include_details=self.debug)
            
            # Add additional headers for client handling
            headers = {
                'X-Error-ID': error_response.error_id,
                'X-Error-Category': error_response.category
            }
            
            if error_response.retryable:
                headers['X-Retryable'] = 'true'
                if error_response.retry_after:
                    headers['Retry-After'] = str(error_response.retry_after)
            
            return JSONResponse(
                status_code=error_response.status_code,
                content=response_data,
                headers=headers
            )
            
        except Exception as handling_error:
            # Fallback error handling
            self.logger.critical(f"Error in error handler: {handling_error}", exc_info=True)
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "id": f"FALLBACK_{uuid.uuid4().hex[:8].upper()}",
                        "category": "internal_server",
                        "message": "An unexpected error occurred in error processing.",
                        "retryable": True,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
    
    async def handle_timeout_error(self, request: Request, context: Dict[str, Any]) -> JSONResponse:
        """Handle timeout errors specifically"""
        
        timeout_error = ErrorResponse(
            error_id=f"TIMEOUT_{uuid.uuid4().hex[:8].upper()}",
            category=ErrorCategory.TIMEOUT,
            message=f"Request timed out after {self.timeout_seconds} seconds",
            status_code=504,
            retryable=True,
            retry_after=120
        )
        
        # Log timeout
        await log_error(
            TimeoutError(f"Request timeout: {self.timeout_seconds}s"),
            context={
                **context,
                'error_id': timeout_error.error_id,
                'timeout_seconds': self.timeout_seconds
            }
        )
        
        response_data = timeout_error.to_dict(include_details=self.debug)
        
        return JSONResponse(
            status_code=timeout_error.status_code,
            content=response_data,
            headers={
                'X-Error-ID': timeout_error.error_id,
                'X-Error-Category': timeout_error.category,
                'X-Retryable': 'true',
                'Retry-After': str(timeout_error.retry_after)
            }
        )
    
    def update_error_tracking(self, category: str) -> None:
        """Update error rate tracking"""
        current_time = time.time()
        
        # Reset counters every hour
        if current_time - self.last_error_reset > 3600:
            self.error_counts.clear()
            self.last_error_reset = current_time
        
        # Increment error count
        self.error_counts[category] = self.error_counts.get(category, 0) + 1
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get current error statistics"""
        return {
            'error_counts': self.error_counts.copy(),
            'active_requests': len(self.request_tracker.active_requests) if self.request_tracker else 0,
            'last_reset': self.last_error_reset,
            'total_errors': sum(self.error_counts.values())
        }


def setup_error_handlers(app: FastAPI) -> None:
    """Setup comprehensive error handlers for FastAPI app"""
    
    logger = get_logger(__name__)
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        error_response = ErrorClassifier.classify_exception(exc)
        
        # Log HTTP exceptions
        await log_error(exc, context={
            'request_id': getattr(request.state, 'request_id', 'unknown'),
            'method': request.method,
            'url': str(request.url),
            'status_code': exc.status_code
        })
        
        return JSONResponse(
            status_code=error_response.status_code,
            content=error_response.to_dict(),
            headers={'X-Error-ID': error_response.error_id}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation exceptions"""
        error_response = ErrorClassifier.classify_exception(exc)
        
        await log_error(exc, context={
            'request_id': getattr(request.state, 'request_id', 'unknown'),
            'validation_errors': exc.errors()
        })
        
        return JSONResponse(
            status_code=error_response.status_code,
            content=error_response.to_dict(),
            headers={'X-Error-ID': error_response.error_id}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle all other exceptions"""
        error_response = ErrorClassifier.classify_exception(exc)
        
        await log_error(exc, context={
            'request_id': getattr(request.state, 'request_id', 'unknown'),
            'method': request.method,
            'url': str(request.url),
            'stack_trace': traceback.format_exc()
        })
        
        return JSONResponse(
            status_code=error_response.status_code,
            content=error_response.to_dict(),
            headers={'X-Error-ID': error_response.error_id}
        )
    
    logger.info("Error handlers configured for FastAPI application")


def add_error_handling_middleware(app: FastAPI, **kwargs) -> ErrorHandlingMiddleware:
    """Add error handling middleware to FastAPI app"""
    
    middleware = ErrorHandlingMiddleware(app, **kwargs)
    app.add_middleware(ErrorHandlingMiddleware, **kwargs)
    
    # Also setup exception handlers
    setup_error_handlers(app)
    
    return middleware