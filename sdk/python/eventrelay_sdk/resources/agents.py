"""Agents resource — dispatch and monitor AI agents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..types import AgentDispatchRequest, AgentDispatchResponse, AgentStatusResponse

if TYPE_CHECKING:
    pass


class AgentsResource:
    """Synchronous agents resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def dispatch(
        self,
        *,
        events: Optional[list[dict[str, Any]]] = None,
        transcript: Optional[str] = None,
        job_id: Optional[str] = None,
        agent_types: Optional[list[str]] = None,
    ) -> AgentDispatchResponse:
        """Dispatch AI agents for the given events.

        When ``events`` is empty or omitted, and ``transcript`` is provided,
        the backend will auto-extract events before dispatching.

        Args:
            events: Pre-extracted event dicts (from :meth:`EventsResource.extract`).
            transcript: Raw transcript — events will be extracted automatically.
            job_id: Job ID whose events should be used.
            agent_types: Restrict dispatch to specific agent type identifiers.

        Returns:
            :class:`AgentDispatchResponse` with a list of
            :class:`AgentExecution` objects, each containing an ``agent_id``.
        """
        payload = AgentDispatchRequest(
            events=events or [],
            transcript=transcript,
            job_id=job_id,
            agent_types=agent_types,
        )
        response = self._client._post(
            "/api/v1/agents/dispatch",
            json=payload.model_dump(exclude_none=True),
        )
        return AgentDispatchResponse.model_validate(response)

    def get_status(self, agent_id: str) -> AgentStatusResponse:
        """Retrieve the current status of a dispatched agent.

        Args:
            agent_id: The ``agent_id`` returned inside an
                :class:`AgentExecution` by :meth:`dispatch`.

        Returns:
            :class:`AgentStatusResponse` with status and optional result.
        """
        response = self._client._get(f"/api/v1/agents/{agent_id}/status")
        return AgentStatusResponse.model_validate(response)


class AsyncAgentsResource:
    """Asynchronous agents resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def dispatch(
        self,
        *,
        events: Optional[list[dict[str, Any]]] = None,
        transcript: Optional[str] = None,
        job_id: Optional[str] = None,
        agent_types: Optional[list[str]] = None,
    ) -> AgentDispatchResponse:
        """Async version of :meth:`AgentsResource.dispatch`."""
        payload = AgentDispatchRequest(
            events=events or [],
            transcript=transcript,
            job_id=job_id,
            agent_types=agent_types,
        )
        response = await self._client._post(
            "/api/v1/agents/dispatch",
            json=payload.model_dump(exclude_none=True),
        )
        return AgentDispatchResponse.model_validate(response)

    async def get_status(self, agent_id: str) -> AgentStatusResponse:
        """Async version of :meth:`AgentsResource.get_status`."""
        response = await self._client._get(f"/api/v1/agents/{agent_id}/status")
        return AgentStatusResponse.model_validate(response)
