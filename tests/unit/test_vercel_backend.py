from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

MODULE_PATH = Path(__file__).parents[2] / "apps" / "backend" / "main.py"
SPEC = spec_from_file_location("uvai_vercel_backend", MODULE_PATH)
assert SPEC and SPEC.loader
backend = module_from_spec(SPEC)
SPEC.loader.exec_module(backend)


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=auJzb1D-fag", "auJzb1D-fag"),
        ("https://youtu.be/auJzb1D-fag", "auJzb1D-fag"),
        ("https://youtube.com/shorts/auJzb1D-fag", "auJzb1D-fag"),
    ],
)
def test_extract_youtube_video_id(url: str, expected: str) -> None:
    assert backend.extract_youtube_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/watch?v=auJzb1D-fag",
        "https://youtube.com.evil.test/watch?v=auJzb1D-fag",
        "file:///etc/passwd",
        "https://user@youtube.com/watch?v=auJzb1D-fag",
        "https://youtube.com/watch?v=../../etc/passwd",
    ],
)
def test_extract_youtube_video_id_rejects_non_youtube_authorities(url: str) -> None:
    with pytest.raises(ValueError):
        backend.extract_youtube_video_id(url)


def test_transcript_action_returns_named_caption_evidence() -> None:
    segments = [
        {
            "text": "This is verified caption evidence from the source video.",
            "start": 0.0,
            "duration": 3.0,
        },
        {
            "text": "It retains source timing instead of inventing speaker labels.",
            "start": 3.0,
            "duration": 4.0,
        },
    ]
    with patch.object(backend, "_fetch_captions", return_value=segments):
        response = TestClient(backend.app).post(
            "/api/v1/transcript-action",
            json={
                "video_url": "https://www.youtube.com/watch?v=auJzb1D-fag",
                "language": "en",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["transcript"]["source"] == "youtube_transcript_api"
    assert body["transcript"]["segments"] == segments


def test_transcript_action_fails_closed_when_provider_fails() -> None:
    with patch.object(
        backend, "_fetch_captions", side_effect=RuntimeError("provider detail")
    ):
        response = TestClient(backend.app).post(
            "/api/v1/transcript-action",
            json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
        )

    body = response.json()
    assert response.status_code == 200
    assert body["success"] is False
    assert body["transcript"]["text"] == ""
    assert body["transcript"]["source"] == "unavailable"
    assert "provider detail" not in str(body)


def test_fetch_captions_routes_through_configured_transport() -> None:
    proxy_config = object()
    fetched = MagicMock()
    fetched.to_raw_data.return_value = [
        {"text": "caption evidence", "start": 1.0, "duration": 2.5}
    ]

    with (
        patch.object(
            backend,
            "_caption_transport",
            return_value=(proxy_config, "webshare_residential"),
        ),
        patch.object(backend, "YouTubeTranscriptApi") as api_class,
    ):
        api_class.return_value.fetch.return_value = fetched
        result = backend._fetch_captions("auJzb1D-fag", "en-US")

    api_class.assert_called_once_with(proxy_config=proxy_config)
    api_class.return_value.fetch.assert_called_once_with(
        "auJzb1D-fag", languages=["en-US", "en"]
    )
    assert result == [
        {"text": "caption evidence", "start": 1.0, "duration": 2.5}
    ]


def test_webshare_credentials_select_residential_transport(monkeypatch) -> None:
    monkeypatch.setenv("WEBSHARE_PROXY_USERNAME", "test-user")
    monkeypatch.setenv("WEBSHARE_PROXY_PASSWORD", "test-password")
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)

    proxy_config, transport = backend._caption_transport()

    assert isinstance(proxy_config, backend.WebshareProxyConfig)
    assert transport == "webshare_residential"
    assert set(proxy_config.to_requests_dict()) == {"http", "https"}


def test_partial_webshare_credentials_fail_closed(monkeypatch) -> None:
    monkeypatch.setenv("WEBSHARE_PROXY_USERNAME", "test-user")
    monkeypatch.delenv("WEBSHARE_PROXY_PASSWORD", raising=False)
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)

    with pytest.raises(backend.CaptionTransportConfigurationError):
        backend._caption_transport()


def test_hosted_health_reports_missing_transport(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("WEBSHARE_PROXY_USERNAME", raising=False)
    monkeypatch.delenv("WEBSHARE_PROXY_PASSWORD", raising=False)
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)

    response = TestClient(backend.app).get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["video_path_ready"] is False
    assert response.json()["caption_transport"] == "direct"


def test_hosted_action_refuses_direct_cloud_egress(monkeypatch) -> None:
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("WEBSHARE_PROXY_USERNAME", raising=False)
    monkeypatch.delenv("WEBSHARE_PROXY_PASSWORD", raising=False)
    monkeypatch.delenv("WEBSHARE_PROXY_URL", raising=False)

    with patch.object(backend, "_fetch_captions") as fetch_captions:
        response = TestClient(backend.app).post(
            "/api/v1/transcript-action",
            json={"video_url": "https://www.youtube.com/watch?v=auJzb1D-fag"},
        )

    fetch_captions.assert_not_called()
    body = response.json()
    assert body["success"] is False
    assert body["metadata"]["caption_transport"] == "direct"
    assert body["transcript"]["source"] == "unavailable"
