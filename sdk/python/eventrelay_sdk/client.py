"""
EventRelay API clients — synchronous and asynchronous.

Both clients expose the same resource-based interface::

    client.videos    → :class:`VideosResource`
    client.events    → :class:`EventsResource`
    client.agents    → :class:`AgentsResource`
    client.transcript → :class:`TranscriptResource`
    client.chat      → :class:`ChatResource`
    client.health    → :class:`HealthResource`
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from .resources.agents import AgentsResource, AsyncAgentsResource
from .types import ApiResponse
from .resources.chat import AsyncChatResource, ChatResource
from .resources.events import AsyncEventsResource, EventsResource
from .resources.health import AsyncHealthResource, HealthResource
from .resources.transcript import AsyncTranscriptResource, TranscriptResource
from .resources.videos import AsyncVideosResource, VideosResource

_DEFAULT_BASE_URL = "https://api.uvai.io"
_DEFAULT_TIMEOUT = 60.0
_DEFAULT_MAX_RETRIES = 2
_RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class EventRelayClient:
    """Synchronous EventRelay API client.

    Args:
        api_key: API key for authentication.  Falls back to the
            ``EVENTRELAY_API_KEY`` environment variable when omitted.
        base_url: Base URL of the EventRelay API server.
            Defaults to ``https://api.uvai.io``.
        timeout: HTTP timeout in seconds (default 60).
        max_retries: Number of retries on transient errors (default 2).
        http_client: Optional pre-configured :class:`httpx.Client` instance.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("EVENTRELAY_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client = http_client or httpx.Client(timeout=timeout)

        # Resource accessors
        self.videos = VideosResource(self)
        self.events = EventsResource(self)
        self.agents = AgentsResource(self)
        self.transcript = TranscriptResource(self)
        self.chat = ChatResource(self)
        self.health = HealthResource(self)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._url(path)
        headers = self._headers()
        attempt = 0
        last_exc: Exception = RuntimeError("No attempts made")
        while attempt <= self._max_retries:
            try:
                response = self._http_client.request(
                    method, url, headers=headers, **kwargs
                )
                if response.status_code in _RETRY_STATUS_CODES and attempt < self._max_retries:
                    attempt += 1
                    continue
                response.raise_for_status()
                data = response.json()
                # Unwrap ApiResponse envelope if present
                if isinstance(data, dict) and "status" in data and "data" in data:
                    api_response = ApiResponse.model_validate(data)
                    return api_response.data
                return data
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS_CODES:
                    raise
                attempt += 1
            except httpx.RequestError as exc:
                last_exc = exc
                attempt += 1
        raise last_exc

    def _get(self, path: str, **kwargs: Any) -> Any:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> Any:
        return self._request("POST", path, **kwargs)

    def _delete(self, path: str, **kwargs: Any) -> Any:
        return self._request("DELETE", path, **kwargs)

    def _put(self, path: str, **kwargs: Any) -> Any:
        return self._request("PUT", path, **kwargs)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "EventRelayClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http_client.close()


class AsyncEventRelayClient:
    """Asynchronous EventRelay API client.

    Args:
        api_key: API key for authentication.  Falls back to the
            ``EVENTRELAY_API_KEY`` environment variable when omitted.
        base_url: Base URL of the EventRelay API server.
        timeout: HTTP timeout in seconds (default 60).
        max_retries: Number of retries on transient errors (default 2).
        http_client: Optional pre-configured :class:`httpx.AsyncClient` instance.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("EVENTRELAY_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client = http_client or httpx.AsyncClient(timeout=timeout)

        # Resource accessors
        self.videos = AsyncVideosResource(self)
        self.events = AsyncEventsResource(self)
        self.agents = AsyncAgentsResource(self)
        self.transcript = AsyncTranscriptResource(self)
        self.chat = AsyncChatResource(self)
        self.health = AsyncHealthResource(self)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._url(path)
        headers = self._headers()
        attempt = 0
        last_exc: Exception = RuntimeError("No attempts made")
        while attempt <= self._max_retries:
            try:
                response = await self._http_client.request(
                    method, url, headers=headers, **kwargs
                )
                if response.status_code in _RETRY_STATUS_CODES and attempt < self._max_retries:
                    attempt += 1
                    continue
                response.raise_for_status()
                data = response.json()
                # Unwrap ApiResponse envelope if present
                if isinstance(data, dict) and "status" in data and "data" in data:
                    api_response = ApiResponse.model_validate(data)
                    return api_response.data
                return data
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS_CODES:
                    raise
                attempt += 1
            except httpx.RequestError as exc:
                last_exc = exc
                attempt += 1
        raise last_exc

    async def _get(self, path: str, **kwargs: Any) -> Any:
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, **kwargs: Any) -> Any:
        return await self._request("POST", path, **kwargs)

    async def _delete(self, path: str, **kwargs: Any) -> Any:
        return await self._request("DELETE", path, **kwargs)

    async def _put(self, path: str, **kwargs: Any) -> Any:
        return await self._request("PUT", path, **kwargs)

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "AsyncEventRelayClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying async HTTP client."""
        await self._http_client.aclose()
