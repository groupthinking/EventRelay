import logging
import time
from typing import Dict, Any, Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Initialize a logger for UCP operations.
# The logger's level can be configured externally (e.g., via logging.basicConfig or file handlers).
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Prometheus Metrics Definitions ---
#
# UCP_REQUEST_TOTAL: Counts the total number of UCP requests.
# Labels:
#   - method: The HTTP method (e.g., 'GET', 'POST', 'PUT', 'DELETE').
#   - status_code: The HTTP status code of the response (e.g., '200', '404', '500').
#                  '0' or 'N/A' can be used for requests that failed before receiving a status code.
UCP_REQUEST_TOTAL = Counter(
    'ucp_requests_total',
    'Total number of UCP requests made.',
    ['method', 'status_code']
)

# UCP_REQUEST_LATENCY_SECONDS: Measures the latency of UCP requests using a histogram.
# Labels:
#   - method: The HTTP method.
#   - status_code: The HTTP status code.
# Buckets: Define ranges for latency observation, allowing for detailed analysis of response times.
UCP_REQUEST_LATENCY_SECONDS = Histogram(
    'ucp_request_latency_seconds',
    'Latency of UCP requests in seconds.',
    ['method', 'status_code'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf'))
)

# UCP_REQUEST_IN_PROGRESS: Tracks the number of UCP requests currently being processed.
# Labels:
#   - method: The HTTP method.
UCP_REQUEST_IN_PROGRESS = Gauge(
    'ucp_requests_in_progress',
    'Number of UCP requests currently in progress.',
    ['method']
)

class UCPMetricsLogger:
    """
    A utility class for detailed logging and Prometheus metrics tracking of UCP
    (Unified Control Plane) requests and responses.

    This class provides methods to:
    1. Log the details of outgoing requests and incoming responses.
    2. Increment counters for total requests and record request latency.
    3. Track the number of concurrent requests in progress.
    4. Expose current metrics in Prometheus exposition format.
    """

    def __init__(self) -> None:
        """
        Initializes the UCPMetricsLogger.
        No specific instance-level state is required as Prometheus metrics are global
        and the logger is configured at the module level.
        """
        pass

    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None
    ) -> None:
        """
        Logs details of an outgoing UCP request and increments the in-progress gauge.

        Args:
            method: The HTTP method (e.g., 'GET', 'POST').
            url: The URL of the request.
            headers: Optional dictionary of request headers.
            body: Optional request body. This can be a string, dict, or bytes.
            request_id: Optional unique identifier for the request, for correlation across logs.
        """
        log_msg = f"UCP Request [{request_id or 'N/A'}]: {method} {url}"
        if headers:
            log_msg += f"\n  Headers: {headers}"
        if body is not None:
            # For large bodies, consider truncating or hashing for logging
            log_msg += f"\n  Body: {body}"
        logger.info(log_msg)

        # Increment the gauge for requests in progress
        UCP_REQUEST_IN_PROGRESS.labels(method=method).inc()

    def log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        latency_seconds: float,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        request_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Logs details of an incoming UCP response, decrements the in-progress gauge,
        and records Prometheus metrics for total requests and latency.

        Args:
            method: The HTTP method of the original request.
            url: The URL of the original request.
            status_code: The HTTP status code of the response. Use 0 or a negative
                         value if no status code was received (e.g., network error).
            latency_seconds: The time taken for the request-response cycle in seconds.
            headers: Optional dictionary of response headers.
            body: Optional response body. This can be a string, dict, or bytes.
            request_id: Optional unique identifier for the request, for correlation across logs.
            error: Optional error message if the request failed at a lower level
                   (e.g., network error, timeout) or if the response indicated an error.
        """
        # Determine log level based on status code or error presence
        log_level_func = logger.info
        if error:
            log_level_func = logger.error
        elif status_code >= 500:
            log_level_func = logger.error
        elif status_code >= 400:
            log_level_func = logger.warning

        log_msg = (
            f"UCP Response [{request_id or 'N/A'}]: {method} {url} "
            f"Status: {status_code} Latency: {latency_seconds:.4f}s"
        )
        if headers:
            log_msg += f"\n  Headers: {headers}"
        if body is not None:
            # For large bodies, consider truncating or hashing for logging
            log_msg += f"\n  Body: {body}"
        if error:
            log_msg += f"\n  Error: {error}"

        log_level_func(log_msg)

        # Decrement the gauge for requests in progress
        UCP_REQUEST_IN_PROGRESS.labels(method=method).dec()

        # Record Prometheus metrics
        # Convert status_code to string for labels, handling cases where it might be 0 or None
        status_code_str = str(status_code) if status_code else '0' # Use '0' for cases without a valid HTTP status
        UCP_REQUEST_TOTAL.labels(method=method, status_code=status_code_str).inc()
        UCP_REQUEST_LATENCY_SECONDS.labels(method=method, status_code=status_code_str).observe(latency_seconds)

    def get_metrics_text(self) -> str:
        """
        Returns the current Prometheus metrics in text exposition format.

        This method is typically used by a Prometheus metrics endpoint (e.g., a web server
        route like `/metrics`) to expose the collected metrics to a Prometheus server.

        Returns:
            A string containing the Prometheus metrics in the required text format.
        """
        return generate_latest().decode('utf-8')