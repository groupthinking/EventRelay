"""Chat resource — conversational AI assistant."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from ..types import ChatRequest, ChatResponse

if TYPE_CHECKING:
    pass


class ChatResource:
    """Synchronous chat resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def send(
        self,
        query: str,
        *,
        video_id: Optional[str] = None,
        video_url: Optional[str] = None,
        context: str = "tooltip-assistant",
        session_id: str = "default",
        history: Optional[list[dict[str, str]]] = None,
    ) -> ChatResponse:
        """Send a message to the AI assistant.

        Args:
            query: User message (max 2000 characters).
            video_id: YouTube video ID for context.
            video_url: YouTube video URL for context.
            context: Context identifier (default ``"tooltip-assistant"``).
            session_id: Conversation session identifier.
            history: Previous conversation turns.

        Returns:
            :class:`ChatResponse` with the assistant's reply.
        """
        payload = ChatRequest(
            query=query,
            video_id=video_id,
            video_url=video_url,
            context=context,
            session_id=session_id,
            history=history,
        )
        response = self._client._post(
            "/api/v1/chat",
            json=payload.model_dump(exclude_none=True),
        )
        return ChatResponse.model_validate(response)


class AsyncChatResource:
    """Asynchronous chat resource."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def send(
        self,
        query: str,
        *,
        video_id: Optional[str] = None,
        video_url: Optional[str] = None,
        context: str = "tooltip-assistant",
        session_id: str = "default",
        history: Optional[list[dict[str, str]]] = None,
    ) -> ChatResponse:
        """Async version of :meth:`ChatResource.send`."""
        payload = ChatRequest(
            query=query,
            video_id=video_id,
            video_url=video_url,
            context=context,
            session_id=session_id,
            history=history,
        )
        response = await self._client._post(
            "/api/v1/chat",
            json=payload.model_dump(exclude_none=True),
        )
        return ChatResponse.model_validate(response)
