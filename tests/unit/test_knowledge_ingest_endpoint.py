from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _install_shared_youtube_stub() -> None:
    if "shared.youtube" in sys.modules:
        return

    shared_module = types.ModuleType("shared")
    youtube_module = types.ModuleType("shared.youtube")

    @dataclass
    class RobustYouTubeMetadata:
        video_id: str = "auJzb1D-fag"

    class RobustYouTubeService: ...

    youtube_module.RobustYouTubeMetadata = RobustYouTubeMetadata
    youtube_module.RobustYouTubeService = RobustYouTubeService
    shared_module.youtube = youtube_module
    sys.modules["shared"] = shared_module
    sys.modules["shared.youtube"] = youtube_module


_install_shared_youtube_stub()

from youtube_extension.backend.api.v1.router import (  # noqa: E402
    get_data_service,
    router,
)


class _FakeDataService:
    def __init__(self, result: dict[str, Any] | None):
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def save_knowledge_entry(
        self, *, text: str, tags: list[str], source: str | None
    ) -> dict[str, Any] | None:
        self.calls.append({"text": text, "tags": tags, "source": source})
        return self.result


def _build_client(fake_data_service: _FakeDataService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_data_service] = lambda: fake_data_service
    return TestClient(app, raise_server_exceptions=False)


def test_knowledge_ingest_success() -> None:
    fake_data_service = _FakeDataService(
        {
            "id": "kb_123",
            "source": "job_abc",
            "tags": ["topic", "followup"],
        }
    )
    client = _build_client(fake_data_service)

    response = client.post(
        "/api/v1/knowledge/ingest",
        json={
            "text": "  transcript-derived insight  ",
            "tags": [" topic ", "", "followup", "topic"],
            "source": " job_abc ",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stored"] is True
    assert body["id"] == "kb_123"
    assert body["source"] == "job_abc"
    assert body["tags"] == ["topic", "followup"]
    assert "Stored insight" in body["message"]


def test_knowledge_ingest_rejects_blank_text() -> None:
    fake_data_service = _FakeDataService(result=None)
    client = _build_client(fake_data_service)

    response = client.post(
        "/api/v1/knowledge/ingest",
        json={"text": "   ", "tags": ["x"], "source": "job_1"},
    )

    assert response.status_code == 400
    assert "non-empty" in response.json()["detail"]
    assert fake_data_service.calls == []


def test_knowledge_ingest_normalizes_optional_tags() -> None:
    fake_data_service = _FakeDataService(
        {"id": "kb_999", "source": "api:v1:knowledge", "tags": []}
    )
    client = _build_client(fake_data_service)

    response = client.post(
        "/api/v1/knowledge/ingest",
        json={"text": "Insight", "tags": "not-an-array"},
    )

    assert response.status_code == 200
    assert response.json()["tags"] == []
    assert fake_data_service.calls[0]["tags"] == []


def test_knowledge_ingest_storage_failure_is_honest() -> None:
    fake_data_service = _FakeDataService(result=None)
    client = _build_client(fake_data_service)

    response = client.post(
        "/api/v1/knowledge/ingest",
        json={"text": "Persist me", "tags": ["alpha"]},
    )

    assert response.status_code == 500
    assert "Failed to store insight" in response.json()["detail"]
