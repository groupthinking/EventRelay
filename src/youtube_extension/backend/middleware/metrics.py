"""
Prometheus Metrics & Structured Logging Middleware
==================================================
Provides HTTP request duration histograms, request counter by method/endpoint/status,
active connections gauge, and structured JSON logs via structlog.
"""

import logging
import time
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

try:
    import structlog
    struct_logger = structlog.get_logger(__name__)
except ImportError:
    struct_logger = None

logger = logging.getLogger(__name__)

# Standard Prometheus histogram buckets for duration
BUCKETS = [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0]


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for gathering Prometheus metrics and structured logging.
    Collects request counts, duration histograms, active connections gauge, and error rates.
    """

    def __init__(self, app: ASGIApp, exempt_paths: Optional[list[str]] = None):
        super().__init__(app)
        self.exempt_paths = exempt_paths or ["/docs", "/redoc", "/openapi.json"]
        logger.info(f"PrometheusMetricsMiddleware initialized. Exempt paths: {self.exempt_paths}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics/logging for exempt paths to keep logs clean
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Dynamically retrieve health_monitoring_service
        try:
            from youtube_extension.backend.containers.service_container import get_service
            health_service = get_service("health_monitoring_service")
        except Exception:
            health_service = None

        correlation_id = request.headers.get("x-correlation-id") or request.headers.get("x-request-id") or "unknown"
        method = request.method
        endpoint = request.url.path

        # 1. Increment active connections gauge
        if health_service:
            health_service.increment_metric("active_connections", 1.0)

        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            status_code = 500
            raise e
        finally:
            duration = time.time() - start_time

            # 2. Decrement active connections gauge
            if health_service:
                health_service.increment_metric("active_connections", -1.0)

                # Record metrics with tags/labels
                status_str = str(status_code)

                # Request count counter
                req_key = f'requests_total{{method="{method}",endpoint="{endpoint}",status="{status_str}"}}'
                health_service.increment_metric(req_key, 1.0)
                health_service.increment_metric("requests_total", 1.0)

                # Error count counter (>= 400)
                if status_code >= 400:
                    err_key = f'request_errors_total{{method="{method}",endpoint="{endpoint}",status="{status_str}"}}'
                    health_service.increment_metric(err_key, 1.0)
                    health_service.increment_metric("request_errors_total", 1.0)

                # Request duration histogram sum and count
                sum_key = f'request_duration_seconds_sum{{method="{method}",endpoint="{endpoint}"}}'
                count_key = f'request_duration_seconds_count{{method="{method}",endpoint="{endpoint}"}}'
                health_service.increment_metric(sum_key, duration)
                health_service.increment_metric(count_key, 1.0)

                # Histogram buckets
                for b in BUCKETS:
                    if duration <= b:
                        bucket_key = f'request_duration_seconds_bucket{{method="{method}",endpoint="{endpoint}",le="{b}"}}'
                        health_service.increment_metric(bucket_key, 1.0)

                # Inf bucket (equivalent to count)
                inf_bucket_key = f'request_duration_seconds_bucket{{method="{method}",endpoint="{endpoint}",le="+Inf"}}'
                health_service.increment_metric(inf_bucket_key, 1.0)

            # 3. Log structured request/response metadata and context
            log_payload = {
                "correlation_id": correlation_id,
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration_seconds": duration,
                "user_context": "anonymous",  # can be extended with auth user context
            }
            if struct_logger:
                struct_logger.info("request_processed", **log_payload)
            else:
                logger.info(f"request_processed: {log_payload}")
