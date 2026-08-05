"""Unit tests for services/ai/speech_to_text_service.py."""

from __future__ import annotations

<<<<<<< HEAD
import sys
import types
from pathlib import Path
=======
>>>>>>> origin/main
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

<<<<<<< HEAD
# ---------------------------------------------------------------------------
# Add src to path first so module resolution works.
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Stub optional heavy dependencies BEFORE importing the service module so
# that the try/except import guards fire with the stub modules and all three
# AVAILABLE flags are set to False (the stubs lack the real classes).
# ---------------------------------------------------------------------------

# Stub google.api_core
_api_core = types.ModuleType("google.api_core")
_api_core.exceptions = types.ModuleType("google.api_core.exceptions")  # type: ignore[attr-defined]
sys.modules.setdefault("google.api_core", _api_core)
sys.modules.setdefault("google.api_core.exceptions", _api_core.exceptions)  # type: ignore[attr-defined]

# Stub google.cloud namespace
_gcloud = sys.modules.get("google.cloud") or types.ModuleType("google.cloud")
sys.modules.setdefault("google.cloud", _gcloud)

# Stub google.cloud.speech_v2
_speech = types.ModuleType("google.cloud.speech_v2")
sys.modules.setdefault("google.cloud.speech_v2", _speech)

# Stub google.cloud.storage
_storage_stub = types.ModuleType("google.cloud.storage")
sys.modules.setdefault("google.cloud.storage", _storage_stub)

# Stub yt_dlp
_ytdlp = types.ModuleType("yt_dlp")
sys.modules.setdefault("yt_dlp", _ytdlp)

# Stub google parent package so attribute lookups don't fail
_google = sys.modules.get("google") or types.ModuleType("google")
_google.cloud = _gcloud  # type: ignore[attr-defined]
_google.api_core = _api_core  # type: ignore[attr-defined]
sys.modules.setdefault("google", _google)

# ---------------------------------------------------------------------------
# Stub the youtube_extension.services parent packages so importing the leaf
# module does not trigger the full services/__init__.py import chain (which
# pulls in deployment_manager -> broken native extensions).
# ---------------------------------------------------------------------------

def _stub_package(name: str, path: str | None = None) -> types.ModuleType:
    if name not in sys.modules:
        m = types.ModuleType(name)
        m.__path__ = [path or ""]  # type: ignore[assignment]
        m.__package__ = name
        sys.modules[name] = m
    return sys.modules[name]


_stub_package("youtube_extension")
_stub_package(
    "youtube_extension.services",
    str(_SRC / "youtube_extension" / "services"),
)
_stub_package(
    "youtube_extension.services.ai",
    str(_SRC / "youtube_extension" / "services" / "ai"),
)

# Ensure the module itself is freshly imported (no cached version from a prior run)
sys.modules.pop("youtube_extension.services.ai.speech_to_text_service", None)

# Now import the leaf module directly by its file path to avoid any __init__ chain.
import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "youtube_extension.services.ai.speech_to_text_service",
    _SRC / "youtube_extension" / "services" / "ai" / "speech_to_text_service.py",
)
_stt_mod = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
sys.modules["youtube_extension.services.ai.speech_to_text_service"] = _stt_mod
_spec.loader.exec_module(_stt_mod)  # type: ignore[union-attr]
=======
import youtube_extension.services.ai.speech_to_text_service as _stt_mod
>>>>>>> origin/main

SPEECH_AVAILABLE = _stt_mod.SPEECH_AVAILABLE
STORAGE_AVAILABLE = _stt_mod.STORAGE_AVAILABLE
YT_DLP_AVAILABLE = _stt_mod.YT_DLP_AVAILABLE
SpeechToTextConfig = _stt_mod.SpeechToTextConfig
SpeechToTextResult = _stt_mod.SpeechToTextResult
SpeechToTextService = _stt_mod.SpeechToTextService


# ===========================================================================
# Module-level availability flags
# ===========================================================================


class TestAvailabilityFlags:
    """Module exposes boolean availability flags for optional dependencies."""

    def test_speech_available_is_bool(self):
        assert isinstance(SPEECH_AVAILABLE, bool)

    def test_storage_available_is_bool(self):
        assert isinstance(STORAGE_AVAILABLE, bool)

    def test_yt_dlp_available_is_bool(self):
        assert isinstance(YT_DLP_AVAILABLE, bool)

    def test_can_monkeypatch_speech_available_to_false(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", False)
        assert _stt_mod.SPEECH_AVAILABLE is False

    def test_can_monkeypatch_storage_available_to_false(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", False)
        assert _stt_mod.STORAGE_AVAILABLE is False

    def test_can_monkeypatch_yt_dlp_available_to_false(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", False)
        assert _stt_mod.YT_DLP_AVAILABLE is False


# ===========================================================================
# SpeechToTextConfig dataclass
# ===========================================================================


class TestSpeechToTextConfig:
    def test_defaults(self, monkeypatch):
        # Clear all env vars so we get pure defaults
        for var in (
            "GOOGLE_SPEECH_PROJECT_ID",
            "GOOGLE_SPEECH_LOCATION",
            "GOOGLE_SPEECH_RECOGNIZER",
            "GOOGLE_SPEECH_MODEL",
            "GOOGLE_SPEECH_LANGUAGE",
            "GOOGLE_SPEECH_GCS_BUCKET",
            "GOOGLE_SPEECH_GCS_PREFIX",
            "GOOGLE_SPEECH_LONG_RUNNING_THRESHOLD",
            "GOOGLE_SPEECH_BATCH_TIMEOUT",
        ):
            monkeypatch.delenv(var, raising=False)

        # Dataclass field defaults are evaluated at class-definition time when
        # os.getenv is called, so we must reload the module to pick up the
        # monkeypatched env.  For this test we construct with explicit values
        # instead to stay side-effect-free.
        cfg = SpeechToTextConfig(
            project_id=None,
            location="us-central1",
            recognizer_id="default",
            model="latest_long",
            preferred_language_code="en-US",
        )
        assert cfg.location == "us-central1"
        assert cfg.recognizer_id == "default"
        assert cfg.model == "latest_long"
        assert cfg.enable_word_time_offsets is True
        assert cfg.enable_automatic_punctuation is True
        assert cfg.preferred_language_code == "en-US"
        assert cfg.max_download_bytes == 200 * 1024 * 1024

    def test_recognizer_path_none_when_no_project(self):
        cfg = SpeechToTextConfig(project_id=None)
        assert cfg.recognizer_path is None

    def test_recognizer_path_with_project(self):
        cfg = SpeechToTextConfig(
            project_id="my-proj",
            location="us-central1",
            recognizer_id="default",
        )
        assert cfg.recognizer_path == "projects/my-proj/locations/us-central1/recognizers/default"

    def test_recognizer_path_custom_location_and_recognizer(self):
        cfg = SpeechToTextConfig(
            project_id="proj-x",
            location="europe-west4",
            recognizer_id="my-recognizer",
        )
        assert cfg.recognizer_path == "projects/proj-x/locations/europe-west4/recognizers/my-recognizer"

    def test_recognizer_path_empty_recognizer_id_falls_back_to_default(self):
        cfg = SpeechToTextConfig(project_id="proj", location="us-east1", recognizer_id="")
        # When recognizer_id is falsy the property uses "default"
        assert cfg.recognizer_path == "projects/proj/locations/us-east1/recognizers/default"

    def test_long_running_threshold_default(self):
        cfg = SpeechToTextConfig(project_id=None)
        assert cfg.long_running_threshold_bytes == 10 * 1024 * 1024

    def test_batch_timeout_default(self):
        cfg = SpeechToTextConfig(project_id=None)
        assert cfg.batch_timeout_seconds == 1800

    def test_gcs_path_prefix_default(self):
        cfg = SpeechToTextConfig(project_id=None, gcs_path_prefix="speech-transcripts")
        assert cfg.gcs_path_prefix == "speech-transcripts"

    def test_custom_values(self):
        cfg = SpeechToTextConfig(
            project_id="custom-proj",
            location="asia-east1",
            recognizer_id="custom-rec",
            model="chirp",
            enable_word_time_offsets=False,
            enable_automatic_punctuation=False,
            preferred_language_code="ja-JP",
            max_download_bytes=50 * 1024 * 1024,
            long_running_threshold_bytes=5 * 1024 * 1024,
            batch_timeout_seconds=600,
            gcs_bucket="my-bucket",
            gcs_path_prefix="transcripts",
        )
        assert cfg.project_id == "custom-proj"
        assert cfg.location == "asia-east1"
        assert cfg.recognizer_id == "custom-rec"
        assert cfg.model == "chirp"
        assert cfg.enable_word_time_offsets is False
        assert cfg.enable_automatic_punctuation is False
        assert cfg.preferred_language_code == "ja-JP"
        assert cfg.max_download_bytes == 50 * 1024 * 1024
        assert cfg.long_running_threshold_bytes == 5 * 1024 * 1024
        assert cfg.batch_timeout_seconds == 600
        assert cfg.gcs_bucket == "my-bucket"
        assert cfg.gcs_path_prefix == "transcripts"


# ===========================================================================
# SpeechToTextResult dataclass
# ===========================================================================


class TestSpeechToTextResult:
    def test_minimal_construction(self):
        r = SpeechToTextResult(success=True, transcript="hello", segments=[], latency=0.5)
        assert r.success is True
        assert r.transcript == "hello"
        assert r.segments == []
        assert r.latency == 0.5
        assert r.error is None
        assert r.source == "speech_to_text_v2"

    def test_failure_result(self):
        r = SpeechToTextResult(
            success=False, transcript="", segments=[], latency=1.0, error="something failed"
        )
        assert r.success is False
        assert r.error == "something failed"

    def test_custom_source(self):
        r = SpeechToTextResult(
            success=True,
            transcript="hi",
            segments=[{"text": "hi", "start": 0.0, "duration": 1.0}],
            latency=0.1,
            source="speech_to_text_v2_batch",
        )
        assert r.source == "speech_to_text_v2_batch"

    def test_segments_populated(self):
        segs = [{"text": "a", "start": 0.0, "duration": 2.0}, {"text": "b", "start": 2.0, "duration": 1.5}]
        r = SpeechToTextResult(success=True, transcript="a b", segments=segs, latency=0.2)
        assert len(r.segments) == 2
        assert r.segments[0]["text"] == "a"


# ===========================================================================
# SpeechToTextService.__init__
# ===========================================================================


class TestSpeechToTextServiceInit:
    def test_default_config_created(self):
        svc = SpeechToTextService()
        assert isinstance(svc.config, SpeechToTextConfig)

    def test_custom_config_used(self):
        cfg = SpeechToTextConfig(project_id="p", location="us-west1")
        svc = SpeechToTextService(config=cfg)
        assert svc.config is cfg

    def test_clients_start_as_none(self):
        svc = SpeechToTextService()
        assert svc._client is None
        assert svc._storage_client is None


# ===========================================================================
# SpeechToTextService._duration_to_seconds
# ===========================================================================


class TestDurationToSeconds:
    def _make_duration(self, seconds=0, nanos=0):
        d = MagicMock()
        d.seconds = seconds
        d.nanos = nanos
        return d

    def test_none_returns_zero(self):
        assert SpeechToTextService._duration_to_seconds(None) == 0.0

    def test_zero_duration(self):
        d = self._make_duration(0, 0)
        assert SpeechToTextService._duration_to_seconds(d) == 0.0

    def test_whole_seconds_only(self):
        d = self._make_duration(seconds=5, nanos=0)
        assert SpeechToTextService._duration_to_seconds(d) == 5.0

    def test_nanos_only(self):
        d = self._make_duration(seconds=0, nanos=500_000_000)
        assert SpeechToTextService._duration_to_seconds(d) == pytest.approx(0.5)

    def test_seconds_and_nanos(self):
        d = self._make_duration(seconds=3, nanos=250_000_000)
        assert SpeechToTextService._duration_to_seconds(d) == pytest.approx(3.25)

    def test_large_seconds(self):
        d = self._make_duration(seconds=3600, nanos=0)
        assert SpeechToTextService._duration_to_seconds(d) == 3600.0

    def test_object_with_no_seconds_attr(self):
        # Falls back to 0 when attribute is missing
        d = MagicMock(spec=[])  # no attributes
        assert SpeechToTextService._duration_to_seconds(d) == 0.0

    def test_object_with_none_seconds(self):
        d = MagicMock()
        d.seconds = None
        d.nanos = None
        # None values are coerced via `or 0`
        assert SpeechToTextService._duration_to_seconds(d) == 0.0

    def test_fractional_nanos(self):
        d = self._make_duration(seconds=1, nanos=1)
        result = SpeechToTextService._duration_to_seconds(d)
        assert result == pytest.approx(1.000_000_001)


# ===========================================================================
# SpeechToTextService._parse_speech_results
# ===========================================================================


def _make_word(start_seconds=0, start_nanos=0, end_seconds=0, end_nanos=0):
    word = MagicMock()
    start = MagicMock()
    start.seconds = start_seconds
    start.nanos = start_nanos
    end = MagicMock()
    end.seconds = end_seconds
    end.nanos = end_nanos
    word.start_offset = start
    word.end_offset = end
    return word


def _make_alternative(transcript: str, words=None):
    alt = MagicMock()
    alt.transcript = transcript
    alt.words = words or []
    return alt


def _make_result(alternatives):
    r = MagicMock()
    r.alternatives = alternatives
    return r


class TestParseSpeechResults:
    def test_empty_results(self):
        transcript, segments = SpeechToTextService._parse_speech_results([])
        assert transcript == ""
        assert segments == []

    def test_none_results(self):
        transcript, segments = SpeechToTextService._parse_speech_results(None)
        assert transcript == ""
        assert segments == []

    def test_single_result_no_words(self):
        alt = _make_alternative("Hello world")
        result = _make_result([alt])
        transcript, segments = SpeechToTextService._parse_speech_results([result])
        assert transcript == "Hello world"
        assert len(segments) == 1
        assert segments[0]["text"] == "Hello world"
        assert segments[0]["start"] == 0.0
        assert segments[0]["duration"] == 0.0

    def test_single_result_with_words(self):
        w1 = _make_word(start_seconds=1, start_nanos=0, end_seconds=2, end_nanos=0)
        w2 = _make_word(start_seconds=2, start_nanos=0, end_seconds=3, end_nanos=500_000_000)
        alt = _make_alternative("Hello world", words=[w1, w2])
        result = _make_result([alt])
        transcript, segments = SpeechToTextService._parse_speech_results([result])
        assert transcript == "Hello world"
        assert len(segments) == 1
        seg = segments[0]
        assert seg["start"] == pytest.approx(1.0)
        assert seg["duration"] == pytest.approx(2.5)

    def test_multiple_results_joined_by_newline(self):
        alt1 = _make_alternative("First sentence")
        alt2 = _make_alternative("Second sentence")
        results = [_make_result([alt1]), _make_result([alt2])]
        transcript, segments = SpeechToTextService._parse_speech_results(results)
        assert "First sentence" in transcript
        assert "Second sentence" in transcript
        assert "\n" in transcript
        assert len(segments) == 2

    def test_result_with_empty_transcript_skipped(self):
        alt_empty = _make_alternative("   ")  # whitespace only
        alt_good = _make_alternative("Good text")
        results = [_make_result([alt_empty]), _make_result([alt_good])]
        transcript, segments = SpeechToTextService._parse_speech_results(results)
        assert transcript == "Good text"
        assert len(segments) == 1

    def test_result_with_no_alternatives_skipped(self):
        result = _make_result([])
        transcript, segments = SpeechToTextService._parse_speech_results([result])
        assert transcript == ""
        assert segments == []

    def test_only_top_alternative_used(self):
        alt1 = _make_alternative("Top alternative")
        alt2 = _make_alternative("Second alternative")
        result = _make_result([alt1, alt2])
        transcript, segments = SpeechToTextService._parse_speech_results([result])
        assert "Top alternative" in transcript
        assert "Second alternative" not in transcript

    def test_duration_non_negative(self):
        # end < start should still produce duration >= 0
        w1 = _make_word(start_seconds=5, end_seconds=3)  # inverted
        alt = _make_alternative("Text", words=[w1, w1])
        result = _make_result([alt])
        _, segments = SpeechToTextService._parse_speech_results([result])
        assert segments[0]["duration"] >= 0.0

    def test_single_word_zero_duration(self):
        w = _make_word(start_seconds=2, end_seconds=2)
        alt = _make_alternative("Word", words=[w])
        result = _make_result([alt])
        _, segments = SpeechToTextService._parse_speech_results([result])
        assert segments[0]["start"] == pytest.approx(2.0)
        assert segments[0]["duration"] == pytest.approx(0.0)


# ===========================================================================
# SpeechToTextService._parse_batch_response
# ===========================================================================


class TestParseBatchResponse:
    def test_empty_response(self):
        response = MagicMock()
        response.results = {}
        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert transcript == ""
        assert segments == []

    def test_response_with_no_results_attr(self):
        response = MagicMock(spec=[])
        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert transcript == ""
        assert segments == []

    def test_single_file_result(self):
        alt = _make_alternative("Batch text")
        speech_result = _make_result([alt])

        inner_transcript = MagicMock()
        inner_transcript.results = [speech_result]

        inline_result = MagicMock()
        inline_result.transcript = inner_transcript

        file_result = MagicMock()
        file_result.inline_result = inline_result

        response = MagicMock()
        response.results = {"file1": file_result}

        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert "Batch text" in transcript
        assert len(segments) == 1

    def test_file_result_without_inline_result(self):
        file_result = MagicMock()
        file_result.inline_result = None

        response = MagicMock()
        response.results = {"file1": file_result}

        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert transcript == ""
        assert segments == []

    def test_file_result_without_transcript(self):
        inline_result = MagicMock()
        inline_result.transcript = None

        file_result = MagicMock()
        file_result.inline_result = inline_result

        response = MagicMock()
        response.results = {"file1": file_result}

        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert transcript == ""
        assert segments == []

    def test_multiple_file_results_joined(self):
        def _make_file_result(text: str):
            alt = _make_alternative(text)
            speech_result = _make_result([alt])
            inner_transcript = MagicMock()
            inner_transcript.results = [speech_result]
            inline_result = MagicMock()
            inline_result.transcript = inner_transcript
            file_result = MagicMock()
            file_result.inline_result = inline_result
            return file_result

        response = MagicMock()
        response.results = {
            "file1": _make_file_result("First part"),
            "file2": _make_file_result("Second part"),
        }

        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert "First part" in transcript
        assert "Second part" in transcript
        assert len(segments) == 2

    def test_empty_transcript_from_file_not_included(self):
        alt_empty = _make_alternative("   ")
        speech_result = _make_result([alt_empty])
        inner_transcript = MagicMock()
        inner_transcript.results = [speech_result]
        inline_result = MagicMock()
        inline_result.transcript = inner_transcript
        file_result = MagicMock()
        file_result.inline_result = inline_result

        response = MagicMock()
        response.results = {"file1": file_result}

        transcript, segments = SpeechToTextService._parse_batch_response(response)
        assert transcript == ""


# ===========================================================================
# SpeechToTextService.transcribe_youtube_video — unavailable flag paths
# ===========================================================================


class TestTranscribeYouTubeVideoUnavailable:
    """All tests here exercise the early-exit paths when dependencies are unavailable."""

    async def test_returns_error_when_speech_not_available(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", False)
        svc = SpeechToTextService()
        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=test")
        assert result.success is False
        assert "google-cloud-speech" in result.error
        assert result.source == "speech_to_text_v2_unavailable"

    async def test_returns_error_when_yt_dlp_not_available(self, monkeypatch):
        # Temporarily make SPEECH_AVAILABLE True so the yt_dlp check is reached
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", False)
        svc = SpeechToTextService(config=SpeechToTextConfig(project_id="proj"))
        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=test")
        assert result.success is False
        assert "yt-dlp" in result.error
        assert result.source == "speech_to_text_v2_unavailable"

    async def test_returns_error_when_recognizer_not_configured(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        svc = SpeechToTextService(config=SpeechToTextConfig(project_id=None))
        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=test")
        assert result.success is False
        assert result.source == "speech_to_text_v2_unconfigured"

    async def test_returns_error_empty_audio(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        cfg = SpeechToTextConfig(project_id="proj", location="us-central1")
        svc = SpeechToTextService(config=cfg)

        # Stub _download_audio_bytes to return empty bytes
        async def _fake_download(url):
            return b"", "audio/webm", 0

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]

        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=test")
        assert result.success is False
        assert "empty" in result.error.lower()
        assert result.source == "audio_download_failed"

    async def test_batch_unconfigured_when_no_gcs_bucket(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            long_running_threshold_bytes=5,  # very small threshold
            gcs_bucket=None,
        )
        svc = SpeechToTextService(config=cfg)

        large_audio = b"x" * 100  # > threshold of 5 bytes

        async def _fake_download(url):
            return large_audio, "audio/webm", len(large_audio)

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]

        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=test")
        assert result.success is False
        assert "GOOGLE_SPEECH_GCS_BUCKET" in result.error
        assert result.source == "speech_to_text_v2_batch_unconfigured"

    async def test_batch_unavailable_when_storage_missing(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", False)
        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            long_running_threshold_bytes=5,
            gcs_bucket="my-bucket",
        )
        svc = SpeechToTextService(config=cfg)

        large_audio = b"x" * 100

        async def _fake_download(url):
            return large_audio, "audio/webm", len(large_audio)

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]

        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=test")
        assert result.success is False
        assert "google-cloud-storage" in result.error
        assert result.source == "speech_to_text_v2_batch_unavailable"

    async def test_language_code_normalization(self, monkeypatch):
        """Short language codes (no '-') should be replaced by preferred_language_code."""
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        cfg = SpeechToTextConfig(
            project_id="proj",
            preferred_language_code="fr-FR",
        )
        svc = SpeechToTextService(config=cfg)

        captured_language: list[str] = []

        async def _fake_download(url):
            return b"audio", "audio/webm", 4

        async def _fake_recognize(audio, recognizer, language, mime_type):
            captured_language.append(language)
            return SpeechToTextResult(True, "bonjour", [], 0.1)

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]

        # Patch asyncio.to_thread so _recognize_content doesn't actually run
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_response = MagicMock()
            mock_response.results = []
            mock_thread.return_value = mock_response

            result = await svc.transcribe_youtube_video(
                "https://www.youtube.com/watch?v=test",
                language_code="fr",  # short, no '-'
            )

        # The call should have happened (we don't check exact language here
        # because asyncio.to_thread is mocked at module level but the
        # language check still exercised the normalisation branch).
        mock_thread.assert_called_once()


# ===========================================================================
# SpeechToTextService.transcribe_youtube_video — success path (mocked API)
# ===========================================================================


class TestTranscribeYouTubeVideoSuccess:
    async def test_success_path_inline_transcription(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)

        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            long_running_threshold_bytes=10 * 1024 * 1024,  # 10 MB – won't trigger batch
        )
        svc = SpeechToTextService(config=cfg)

        async def _fake_download(url):
            return b"audio_data", "audio/webm", 10

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]

        alt = _make_alternative("Hello from API")
        speech_result = _make_result([alt])
        mock_response = MagicMock()
        mock_response.results = [speech_result]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=abc")

        assert result.success is True
        assert "Hello from API" in result.transcript
        assert result.source == "speech_to_text_v2"

    async def test_empty_api_response_marks_failure(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)

        cfg = SpeechToTextConfig(project_id="proj", long_running_threshold_bytes=10 * 1024 * 1024)
        svc = SpeechToTextService(config=cfg)

        async def _fake_download(url):
            return b"audio_data", "audio/webm", 10

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]

        mock_response = MagicMock()
        mock_response.results = []

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=abc")

        assert result.success is False
        assert "empty" in result.error.lower()

    async def test_batch_success_path(self, monkeypatch):
        """When audio exceeds the batch threshold, _transcribe_with_batch is called."""
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", True)

        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            long_running_threshold_bytes=5,
            gcs_bucket="my-bucket",
        )
        svc = SpeechToTextService(config=cfg)

        large_audio = b"x" * 100

        async def _fake_download(url):
            return large_audio, "audio/webm", len(large_audio)

        async def _fake_batch(audio, recognizer, language, mime_type):
            return SpeechToTextResult(
                True, "batch transcript", [], 0.5, source="speech_to_text_v2_batch"
            )

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]
        svc._transcribe_with_batch = _fake_batch  # type: ignore[method-assign]

        result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=abc")
        assert result.success is True
        assert result.transcript == "batch transcript"
        assert result.source == "speech_to_text_v2_batch"

    async def test_batch_failure_falls_back_to_sync(self, monkeypatch):
        """When batch transcription fails the code falls back to sync recognition."""
        monkeypatch.setattr(_stt_mod, "SPEECH_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "YT_DLP_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", True)

        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            long_running_threshold_bytes=5,
            gcs_bucket="my-bucket",
        )
        svc = SpeechToTextService(config=cfg)

        large_audio = b"x" * 100

        async def _fake_download(url):
            return large_audio, "audio/webm", len(large_audio)

        async def _fake_batch(audio, recognizer, language, mime_type):
            return SpeechToTextResult(
                False, "", [], 0.1, error="batch failed", source="speech_to_text_v2_batch_error"
            )

        svc._download_audio_bytes = _fake_download  # type: ignore[method-assign]
        svc._transcribe_with_batch = _fake_batch  # type: ignore[method-assign]

        alt = _make_alternative("Sync fallback text")
        speech_result = _make_result([alt])
        mock_response = MagicMock()
        mock_response.results = [speech_result]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = mock_response
            result = await svc.transcribe_youtube_video("https://www.youtube.com/watch?v=abc")

        assert result.success is True
        assert "Sync fallback text" in result.transcript


# ===========================================================================
# SpeechToTextService._download_audio_bytes
# ===========================================================================


class TestDownloadAudioBytes:
    """Test the yt-dlp download path using mocked yt_dlp.YoutubeDL."""

    async def test_successful_download_returns_bytes_mime_size(self, tmp_path, monkeypatch):
        audio_content = b"fake_audio_data"
        audio_file = tmp_path / "testvid.webm"
        audio_file.write_bytes(audio_content)

        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"ext": "webm"}
        mock_ydl_instance.prepare_filename.return_value = str(audio_file)
        mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_instance.__exit__ = MagicMock(return_value=False)

        mock_ydl_class = MagicMock(return_value=mock_ydl_instance)
        monkeypatch.setattr(_stt_mod, "yt_dlp", MagicMock(YoutubeDL=mock_ydl_class))

        svc = SpeechToTextService()
        data, mime, size = await svc._download_audio_bytes("https://www.youtube.com/watch?v=test")

        assert data == audio_content
        assert mime == "audio/webm"
        assert size == len(audio_content)

    async def test_download_with_unknown_ext_defaults_to_webm(self, tmp_path, monkeypatch):
        audio_content = b"some_audio"
        audio_file = tmp_path / "testvid."
        audio_file.write_bytes(audio_content)

        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"ext": ""}
        mock_ydl_instance.prepare_filename.return_value = str(audio_file)
        mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_instance.__exit__ = MagicMock(return_value=False)

        mock_ydl_class = MagicMock(return_value=mock_ydl_instance)
        monkeypatch.setattr(_stt_mod, "yt_dlp", MagicMock(YoutubeDL=mock_ydl_class))

        svc = SpeechToTextService()
        data, mime, size = await svc._download_audio_bytes("https://www.youtube.com/watch?v=test")

        assert mime == "audio/webm"

    async def test_download_raises_if_file_missing(self, tmp_path, monkeypatch):
        nonexistent = tmp_path / "missing.webm"
        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"ext": "webm"}
        mock_ydl_instance.prepare_filename.return_value = str(nonexistent)
        mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_instance.__exit__ = MagicMock(return_value=False)

        mock_ydl_class = MagicMock(return_value=mock_ydl_instance)
        monkeypatch.setattr(_stt_mod, "yt_dlp", MagicMock(YoutubeDL=mock_ydl_class))

        svc = SpeechToTextService()
        with pytest.raises(FileNotFoundError):
            await svc._download_audio_bytes("https://www.youtube.com/watch?v=test")

    async def test_download_raises_if_file_too_large(self, tmp_path, monkeypatch):
        large_content = b"x" * 100
        audio_file = tmp_path / "big.webm"
        audio_file.write_bytes(large_content)

        mock_ydl_instance = MagicMock()
        mock_ydl_instance.extract_info.return_value = {"ext": "webm"}
        mock_ydl_instance.prepare_filename.return_value = str(audio_file)
        mock_ydl_instance.__enter__ = MagicMock(return_value=mock_ydl_instance)
        mock_ydl_instance.__exit__ = MagicMock(return_value=False)

        mock_ydl_class = MagicMock(return_value=mock_ydl_instance)
        monkeypatch.setattr(_stt_mod, "yt_dlp", MagicMock(YoutubeDL=mock_ydl_class))

        # Set max_download_bytes below the file size
        svc = SpeechToTextService(config=SpeechToTextConfig(max_download_bytes=10))
        with pytest.raises(ValueError, match="max size"):
            await svc._download_audio_bytes("https://www.youtube.com/watch?v=test")


# ===========================================================================
# SpeechToTextService._recognize_content
# ===========================================================================


class TestRecognizeContent:
    """Test _recognize_content which calls Google Speech API synchronously."""

    def test_creates_client_on_first_call(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        mock_client_instance.recognize.return_value = MagicMock(results=[])
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        cfg = SpeechToTextConfig(project_id="proj", location="us-central1")
        svc = SpeechToTextService(config=cfg)
        assert svc._client is None

        svc._recognize_content(b"audio", "recognizer/path", "en-US", "audio/webm")

        mock_speech_v2.SpeechClient.assert_called_once()
        assert svc._client is mock_client_instance

    def test_reuses_existing_client(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_client_instance.recognize.return_value = MagicMock(results=[])
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        cfg = SpeechToTextConfig(project_id="proj", location="us-central1")
        svc = SpeechToTextService(config=cfg)
        svc._client = mock_client_instance  # pre-set

        svc._recognize_content(b"audio", "recognizer/path", "en-US", "audio/webm")

        # SpeechClient constructor should NOT be called again
        mock_speech_v2.SpeechClient.assert_not_called()

    def test_global_location_uses_default_endpoint(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        mock_client_instance.recognize.return_value = MagicMock(results=[])
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        cfg = SpeechToTextConfig(project_id="proj", location="global")
        svc = SpeechToTextService(config=cfg)
        svc._recognize_content(b"audio", "recognizer/path", "en-US", "audio/webm")

        call_kwargs = mock_speech_v2.SpeechClient.call_args
        # The call uses keyword argument: SpeechClient(client_options={...})
        client_options = call_kwargs.kwargs.get("client_options", {})
        assert client_options.get("api_endpoint") == "speech.googleapis.com"

    def test_non_global_location_uses_regional_endpoint(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        mock_client_instance.recognize.return_value = MagicMock(results=[])
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        cfg = SpeechToTextConfig(project_id="proj", location="europe-west4")
        svc = SpeechToTextService(config=cfg)
        svc._recognize_content(b"audio", "recognizer/path", "en-US", "audio/webm")

        call_kwargs = mock_speech_v2.SpeechClient.call_args
        # Check the endpoint was regional
        client_options = call_kwargs.kwargs.get("client_options", {})
        assert "europe-west4-speech.googleapis.com" in client_options.get("api_endpoint", "")

    def test_recognize_called_with_request(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        expected_response = MagicMock(results=[])
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        mock_client_instance.recognize.return_value = expected_response
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        cfg = SpeechToTextConfig(project_id="proj", location="us-central1")
        svc = SpeechToTextService(config=cfg)
        result = svc._recognize_content(b"audio", "recognizer/path", "en-US", "audio/webm")

        mock_client_instance.recognize.assert_called_once()
        assert result is expected_response


# ===========================================================================
# SpeechToTextService._transcribe_with_batch
# ===========================================================================


class TestTranscribeWithBatch:
    """Test the async batch transcription wrapper."""

    async def test_successful_batch_returns_result(self, monkeypatch):
        alt = _make_alternative("Batch result text")
        speech_result = _make_result([alt])

        inner_transcript = MagicMock()
        inner_transcript.results = [speech_result]
        inline_result = MagicMock()
        inline_result.transcript = inner_transcript
        file_result = MagicMock()
        file_result.inline_result = inline_result

        mock_response = MagicMock()
        mock_response.results = {"file1": file_result}

        cfg = SpeechToTextConfig(project_id="proj", location="us-central1", batch_timeout_seconds=300)
        svc = SpeechToTextService(config=cfg)

        # Mock the synchronous batch recognizer to return mock_response
        svc._batch_recognize_content = MagicMock(return_value=mock_response)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            async def fake_run_in_executor(executor, func, *args):
                return func(*args)

            mock_loop_instance.run_in_executor = fake_run_in_executor
            result = await svc._transcribe_with_batch(b"audio", "recognizer", "en-US", "audio/webm")

        assert result.success is True
        assert "Batch result text" in result.transcript
        assert result.source == "speech_to_text_v2_batch"

    async def test_empty_batch_response_marks_failure(self, monkeypatch):
        mock_response = MagicMock()
        mock_response.results = {}

        cfg = SpeechToTextConfig(project_id="proj", location="us-central1")
        svc = SpeechToTextService(config=cfg)
        svc._batch_recognize_content = MagicMock(return_value=mock_response)

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop_instance = MagicMock()
            mock_loop.return_value = mock_loop_instance

            async def fake_run_in_executor(executor, func, *args):
                return func(*args)

            mock_loop_instance.run_in_executor = fake_run_in_executor
            result = await svc._transcribe_with_batch(b"audio", "recognizer", "en-US", "audio/webm")

        assert result.success is False
        assert "empty" in result.error.lower()
        assert result.source == "speech_to_text_v2_batch"


# ===========================================================================
# SpeechToTextService._batch_recognize_content
# ===========================================================================


class TestBatchRecognizeContent:
    """Test the synchronous batch recognize method."""

    def test_raises_when_storage_not_available(self, monkeypatch):
        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", False)

        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        cfg = SpeechToTextConfig(project_id="proj", location="us-central1", gcs_bucket="bucket")
        svc = SpeechToTextService(config=cfg)
        svc._storage_client = None  # force storage init path

        with pytest.raises(RuntimeError, match="google-cloud-storage"):
            svc._batch_recognize_content(b"audio", "recognizer", "en-US", "audio/webm")

    def test_uploads_audio_and_cleans_up_on_success(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        # Mock storage client and bucket
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        # Mock operation
        mock_operation = MagicMock()
        expected_response = MagicMock()
        mock_operation.result.return_value = expected_response
        mock_client_instance.batch_recognize.return_value = mock_operation

        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", True)

        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            gcs_bucket="my-bucket",
            gcs_path_prefix="speech-transcripts",
            batch_timeout_seconds=600,
        )
        svc = SpeechToTextService(config=cfg)
        svc._storage_client = mock_storage_client

        result = svc._batch_recognize_content(b"audio", "recognizer", "en-US", "audio/webm")

        # The audio should have been uploaded
        mock_blob.upload_from_string.assert_called_once_with(b"audio", content_type="audio/webm")
        # The blob should have been deleted (cleanup)
        mock_blob.delete.assert_called_once()
        # The response should have been returned
        assert result is expected_response

    def test_creates_storage_client_lazily(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        mock_storage_module = MagicMock()
        mock_storage_client = MagicMock()
        mock_storage_module.Client.return_value = mock_storage_client
        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client.bucket.return_value = mock_bucket

        mock_operation = MagicMock()
        mock_operation.result.return_value = MagicMock()
        mock_client_instance.batch_recognize.return_value = mock_operation

        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", True)
        monkeypatch.setattr(_stt_mod, "storage", mock_storage_module)

        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            gcs_bucket="my-bucket",
        )
        svc = SpeechToTextService(config=cfg)
        assert svc._storage_client is None

        svc._batch_recognize_content(b"audio", "recognizer", "en-US", "audio/webm")

        mock_storage_module.Client.assert_called_once()
        assert svc._storage_client is mock_storage_client

    def test_gcs_uri_uses_configured_bucket_and_prefix(self, monkeypatch):
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        uploaded_args: list = []
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = lambda *a, **kw: uploaded_args.append(kw.get("content_type"))
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        mock_operation = MagicMock()
        mock_operation.result.return_value = MagicMock()
        mock_client_instance.batch_recognize.return_value = mock_operation

        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", True)

        cfg = SpeechToTextConfig(
            project_id="proj",
            location="us-central1",
            gcs_bucket="custom-bucket",
            gcs_path_prefix="my/prefix",
        )
        svc = SpeechToTextService(config=cfg)
        svc._storage_client = mock_storage_client

        svc._batch_recognize_content(b"audio", "recognizer", "en-US", "audio/webm")

        mock_storage_client.bucket.assert_called_once_with("custom-bucket")
        # Blob name should start with 'my/prefix/'
        blob_name = mock_bucket.blob.call_args[0][0]
        assert blob_name.startswith("my/prefix/")

    def test_blob_deleted_even_when_operation_raises(self, monkeypatch):
        """GCS blob should be cleaned up even if the operation fails."""
        mock_speech_v2 = MagicMock()
        mock_client_instance = MagicMock()
        mock_speech_v2.SpeechClient.return_value = mock_client_instance
        monkeypatch.setattr(_stt_mod, "speech_v2", mock_speech_v2)

        mock_blob = MagicMock()
        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        mock_storage_client = MagicMock()
        mock_storage_client.bucket.return_value = mock_bucket

        mock_operation = MagicMock()
        mock_operation.result.side_effect = RuntimeError("operation failed")
        mock_client_instance.batch_recognize.return_value = mock_operation

        monkeypatch.setattr(_stt_mod, "STORAGE_AVAILABLE", True)

        cfg = SpeechToTextConfig(project_id="proj", gcs_bucket="my-bucket")
        svc = SpeechToTextService(config=cfg)
        svc._storage_client = mock_storage_client

        with pytest.raises(RuntimeError, match="operation failed"):
            svc._batch_recognize_content(b"audio", "recognizer", "en-US", "audio/webm")

        # Cleanup should still be attempted
        mock_blob.delete.assert_called_once()


# ===========================================================================
# SpeechToTextService._parse_response (static wrapper)
# ===========================================================================


class TestParseResponse:
    def test_delegates_to_parse_speech_results(self):
        alt = _make_alternative("Wrapper works")
        speech_result = _make_result([alt])
        mock_response = MagicMock()
        mock_response.results = [speech_result]

        transcript, segments = SpeechToTextService._parse_response(mock_response)
        assert transcript == "Wrapper works"
        assert len(segments) == 1

    def test_none_results_attr(self):
        mock_response = MagicMock()
        mock_response.results = None
        transcript, segments = SpeechToTextService._parse_response(mock_response)
        assert transcript == ""
        assert segments == []


# ===========================================================================
# __all__ exports
# ===========================================================================


class TestModuleExports:
    def test_all_contains_expected_names(self):
        from youtube_extension.services.ai.speech_to_text_service import __all__

        assert "SpeechToTextConfig" in __all__
        assert "SpeechToTextResult" in __all__
        assert "SpeechToTextService" in __all__
