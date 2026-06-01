"""Health resource — API health and readiness checks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..types import HealthResponse

if TYPE_CHECKING:
    pass


class HealthResource:
    """Synchronous health resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def check(self) -> HealthResponse:
        """Perform a basic health check.

        Returns:
            :class:`HealthResponse` with ``status`` field.
        """
        response = self._client._get("/api/v1/health")
        return HealthResponse.model_validate(response)

    def detailed(self) -> HealthResponse:
        """Perform a detailed health check including all sub-services.

        Returns:
            :class:`HealthResponse` with ``components`` breakdown.
        """
        response = self._client._get("/api/v1/health/detailed")
        return HealthResponse.model_validate(response)


class AsyncHealthResource:
    """Asynchronous health resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def check(self) -> HealthResponse:
        """Async version of :meth:`HealthResource.check`."""
        response = await self._client._get("/api/v1/health")
        return HealthResponse.model_validate(response)

    async def detailed(self) -> HealthResponse:
        """Async version of :meth:`HealthResource.detailed`."""
        response = await self._client._get("/api/v1/health/detailed")
        return HealthResponse.model_validate(response)
