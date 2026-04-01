"""Resource sub-modules for the EventRelay SDK."""

from .agents import AgentsResource, AsyncAgentsResource
from .chat import AsyncChatResource, ChatResource
from .events import AsyncEventsResource, EventsResource
from .health import AsyncHealthResource, HealthResource
from .transcript import AsyncTranscriptResource, TranscriptResource
from .videos import AsyncVideosResource, VideosResource

__all__ = [
    "VideosResource",
    "AsyncVideosResource",
    "EventsResource",
    "AsyncEventsResource",
    "AgentsResource",
    "AsyncAgentsResource",
    "TranscriptResource",
    "AsyncTranscriptResource",
    "ChatResource",
    "AsyncChatResource",
    "HealthResource",
    "AsyncHealthResource",
]
