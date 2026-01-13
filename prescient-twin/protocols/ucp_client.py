import logging
from typing import Any, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class UCPClient:
    """
    A core UCP client module responsible for sending and receiving UCP-formatted
    requests and responses over HTTP.

    This client handles the underlying HTTP communication using `httpx` and
    provides an interface for interacting with a UCP server. It assumes UCP
    messages are represented as Python dictionaries that are serialized to JSON
    for transmission and deserialized from JSON upon reception.
    If the UCP protocol requires a different serialization format (e.g., XML,
    form-encoded), the `send_request` method would need to be adapted accordingly.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        headers: Optional[dict[str, str]] = None,
        auth: Optional[httpx.Auth] = None,
        verify_ssl: bool = True,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ) -> None:
        """
        Initializes the UCPClient.

        Args:
            base_url: The base URL of the UCP server (e.g., "https://ucp.example.com/api/v1").
            timeout: The default timeout for HTTP requests in seconds.
            headers: Optional dictionary of default HTTP headers to send with all requests.
            auth: Optional `httpx.Auth` object for authentication (e.g., `httpx.BasicAuth`).
            verify_ssl: Whether to verify SSL certificates for HTTPS requests.
            max_retries: The maximum number of times to retry a failed request (excluding the first attempt).
                         A value of 0 means no retries.
            backoff_factor: The factor by which to multiply the delay between retries (e.g., 0.5, 1, 2).
                            Used with exponential backoff.
        """
        if not base_url:
            raise ValueError("base_url cannot be empty.")

        self._base_url = base_url
        self._timeout = timeout
        self._headers = headers if headers is not None else {}
        self._auth = auth
        self._verify_ssl = verify_ssl
        self._client: Optional[httpx.AsyncClient] = None
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._logger = logging.getLogger(self.__class__.__name__)

        # Initialize the AsyncRetrying instance for this client
        self._retryer = AsyncRetrying(
            stop=stop_after_attempt(
                self._max_retries + 1
            ),  # +1 because initial attempt is not a retry
            wait=wait_exponential(multiplier=self._backoff_factor, min=1, max=60),
            retry=(
                retry_if_exception_type(
                    httpx.RequestError
                )  # Network errors, timeouts, connection issues
                | retry_if_exception(
                    self._is_transient_http_error
                )  # Custom predicate for transient HTTP errors
            ),
            before_sleep=before_sleep_log(self._logger, logging.WARNING, exc_info=True),
            reraise=True,  # Re-raise the last exception if all retries fail
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Lazily initializes and returns the `httpx.AsyncClient` instance.
        This ensures the client is only created when needed and allows for
        proper resource management with `__aenter__` and `__aexit__`.
        """
        if self._client is None:
            self._logger.debug(f"Initializing httpx.AsyncClient for {self._base_url}")
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=self._headers,
                auth=self._auth,
                verify=self._verify_ssl,
            )
        return self._client

    async def _close_client(self) -> None:
        """
        Closes the underlying `httpx.AsyncClient` if it exists.
        """
        if self._client is not None:
            self._logger.debug("Closing httpx.AsyncClient.")
            await self._client.aclose()
            self._client = None

    def _is_transient_http_error(self, exception: BaseException) -> bool:
        """
        Predicate to determine if an HTTPStatusError is transient and should be retried.
        This method is called by tenacity's `retry_if_exception`.
        """
        if isinstance(exception, httpx.HTTPStatusError):
            # Common transient HTTP status codes:
            # 408 Request Timeout (client-side timeout, but server might still be processing)
            # 429 Too Many Requests
            # 500 Internal Server Error (often transient)
            # 502 Bad Gateway
            # 503 Service Unavailable
            # 504 Gateway Timeout
            transient_codes = {408, 429, 500, 502, 503, 504}
            status_code = exception.response.status_code
            return status_code in transient_codes
        return False

    async def send_request(
        self,
        endpoint: str,
        ucp_payload: dict[str, Any],
        method: str = "POST",
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> dict[str, Any]:
        """
        Sends a UCP-formatted request to the specified endpoint and returns the
        UCP-formatted response.

        The `ucp_payload` dictionary is serialized to JSON for the request body.
        The response is expected to be JSON and is deserialized into a dictionary.

        Args:
            endpoint: The API endpoint relative to the base URL (e.g., "/send_message").
            ucp_payload: A dictionary representing the UCP request body. This will be
                          serialized to JSON and sent as the request body.
            method: The HTTP method to use for the request (e.g., "POST", "GET", "PUT").
                    Defaults to "POST".
            headers: Optional additional HTTP headers for this specific request,
                     which will override any default client headers if keys conflict.
            params: Optional dictionary of query parameters to append to the URL.
            timeout: Optional timeout for this specific request in seconds,
                     overriding the client's default timeout.

        Returns:
            A dictionary representing the UCP response body, deserialized from JSON.

        Raises:
            httpx.HTTPStatusError: If the HTTP response indicates an error (status code >= 400)
                                   and it's not a transient error that was retried.
            httpx.RequestError: For network-related errors (e.g., connection refused, timeout)
                                after all retries have failed.
            ValueError: If the response body cannot be parsed as JSON.
            Exception: For any other unexpected errors during the request.
        """
        client = await self._get_client()
        request_headers = self._headers.copy()
        request_headers.update({"Content-Type": "application/json"})
        if headers:
            request_headers.update(headers)

        request_url_for_log = f"{self._base_url}{endpoint}"  # For logging context

        async for attempt in self._retryer:
            with attempt:
                try:
                    self._logger.debug(
                        f"Sending {method.upper()} request to {request_url_for_log} "
                        f"(attempt {attempt.retry_state.attempt_number}/{self._max_retries + 1}) "
                        f"with payload: {ucp_payload}"
                    )
                    response = await client.request(
                        method=method.upper(),
                        url=endpoint,  # httpx handles joining base_url and endpoint
                        json=ucp_payload,
                        headers=request_headers,
                        params=params,
                        timeout=timeout if timeout is not None else self._timeout,
                    )
                    response.raise_for_status()  # Raise an exception for 4xx/5xx responses

                    # Assuming UCP responses are JSON
                    response_data = response.json()
                    self._logger.debug(
                        f"Received successful response from {request_url_for_log}: {response_data}"
                    )
                    return response_data
                except httpx.HTTPStatusError as e:
                    # Log the error. tenacity's before_sleep_log will handle retry logging if transient.
                    # If it's not a transient error, it will be re-raised after all attempts.
                    log_level = (
                        self._logger.warning
                        if self._is_transient_http_error(e)
                        else self._logger.error
                    )
                    log_level(
                        f"UCP HTTP error {e.response.status_code} for {e.request.url!r}. "
                        f"Response: {e.response.text[:200]}..."
                        if e.response.text
                        else "No response text.",
                        exc_info=True,  # Include traceback for debugging
                    )
                    raise httpx.HTTPStatusError(
                        f"UCP HTTP error {e.response.status_code} for {e.request.url!r}: {e.response.text}",
                        request=e.request,
                        response=e.response,
                    ) from e
                except httpx.RequestError as e:
                    # Log network/request errors. tenacity's before_sleep_log will handle retry logging.
                    self._logger.error(
                        f"UCP network error while requesting {e.request.url!r}: {e}. "
                        f"Details: {type(e).__name__} - {e}",
                        exc_info=True,  # Include traceback for debugging
                    )
                    raise httpx.RequestError(
                        f"UCP network error while requesting {e.request.url!r}: {e}",
                        request=e.request,
                    ) from e
                except ValueError as e:
                    # This occurs if response.json() fails, indicating malformed JSON or an unexpected content type.
                    # It's not a transient network error, so retrying is unlikely to help.
                    # Log the error and re-raise it immediately.
                    response_text_preview = (
                        response.text[:200]
                        if response.text
                        else "No response text available."
                    )
                    self._logger.error(
                        f"Failed to parse JSON response from {request_url_for_log}: {e}. "
                        f"Raw response (first 200 chars): {response_text_preview}",
                        exc_info=True,  # Include traceback for debugging
                    )
                    raise ValueError(
                        f"Failed to parse JSON response from {request_url_for_log}: {e}"
                    ) from e
                except Exception as e:
                    # Catch any other unexpected errors during the request process.
                    # These are generally not retriable and indicate a deeper issue.
                    self._logger.error(
                        f"An unexpected error occurred during UCP request to {request_url_for_log}: {e}. "
                        f"Details: {type(e).__name__} - {e}",
                        exc_info=True,  # Include traceback for debugging
                    )
                    raise Exception(
                        f"Unexpected error during UCP request to {request_url_for_log}: {e}"
                    ) from e
