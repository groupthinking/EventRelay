import threading
from types import SimpleNamespace

import pytest

from src.integration.gemini_agentic_video import (
    GeminiAgenticVideoService,
    VideoInput,
)


class FakeInteractions:
    def __init__(self) -> None:
        self.request = None
        self.thread_id = None

    def create(self, **kwargs):
        self.request = kwargs
        self.thread_id = threading.get_ident()
        return SimpleNamespace(
            steps=[
                SimpleNamespace(
                    content=[SimpleNamespace(text="grounded result"), SimpleNamespace()]
                )
            ],
            usage=SimpleNamespace(total_tokens=321),
        )


@pytest.mark.asyncio
async def test_agentic_youtube_request_returns_execution_receipt():
    interactions = FakeInteractions()
    client = SimpleNamespace(interactions=interactions)
    service = GeminiAgenticVideoService(client=client)
    caller_thread_id = threading.get_ident()

    receipt = await service.analyze(
        [VideoInput("https://youtu.be/auJzb1D-fag")],
        "Find the implementation steps and their timestamps.",
    )

    assert interactions.request == {
        "model": "gemini-3.7-flash",
        "input": [
            {
                "type": "video",
                "uri": "https://youtu.be/auJzb1D-fag",
                "processing": "agentic",
            },
            {
                "type": "text",
                "text": "Find the implementation steps and their timestamps.",
            },
        ],
    }
    assert interactions.thread_id != caller_thread_id
    assert receipt.output_text == "grounded result"
    assert receipt.total_tokens == 321
    assert receipt.model == "gemini-3.7-flash"
    assert receipt.sources == ("https://youtu.be/auJzb1D-fag",)
    assert receipt.processing_modes == ("agentic",)


def test_mixed_mode_keeps_each_video_processing_policy():
    request_input = GeminiAgenticVideoService.build_input(
        [
            VideoInput("gs://bucket/reference.mp4", "agentic", "video/mp4"),
            VideoInput("gs://bucket/clip.mp4", "static", "video/mp4"),
        ],
        "Locate the clip in the reference recording.",
    )

    assert request_input[0]["processing"] == "agentic"
    assert request_input[1]["processing"] == "static"
    assert request_input[0]["mime_type"] == "video/mp4"


@pytest.mark.parametrize(
    "uri",
    ["x", "https://example.com/video.mp4", "ftp://youtu.be/auJzb1D-fag"],
)
@pytest.mark.asyncio
async def test_malformed_video_uri_fails_before_calling_provider(uri):
    interactions = FakeInteractions()
    service = GeminiAgenticVideoService(client=SimpleNamespace(interactions=interactions))

    with pytest.raises(ValueError):
        await service.analyze([VideoInput(uri)], "question")

    assert interactions.request is None


@pytest.mark.parametrize(
    ("videos", "prompt"),
    [([], "question"), ([VideoInput("")], "question"), ([VideoInput("x")], " ")],
)
def test_invalid_requests_fail_before_calling_provider(videos, prompt):
    with pytest.raises(ValueError):
        GeminiAgenticVideoService.build_input(videos, prompt)


def test_invalid_processing_mode_fails_validation():
    with pytest.raises(ValueError):
        GeminiAgenticVideoService.build_input(
            [VideoInput("gs://bucket/clip.mp4", "dynamic", "video/mp4")],
            "question",
        )
