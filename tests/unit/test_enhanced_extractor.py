"""Unit tests for processors/enhanced_extractor.py."""

from __future__ import annotations

import importlib.util as importlib_util
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure src/ is on the path before any project imports
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Load the legacy extractor with local-only optional-dependency substitutes.
# The old tests installed bare modules in global ``sys.modules`` at collection
# time, so unrelated tests observed fake Google/YouTube packages. Loading the
# target under a private name keeps those substitutes scoped to this import.
# ---------------------------------------------------------------------------

_gcapi = types.ModuleType("googleapiclient")
_gcapi.discovery = types.ModuleType("googleapiclient.discovery")
_gcapi.errors = types.ModuleType("googleapiclient.errors")
_gcapi.errors.HttpError = Exception

_tr = types.ModuleType("transformers")
_tr.pipeline = None

_openai_stub = types.ModuleType("openai")
_openai_stub.AsyncOpenAI = MagicMock()

_pd = types.ModuleType("pandas")


class _FakeDataFrame:
    def __init__(self, data=None):
        self._data = data or []

    def to_csv(self, path, index=False):
        with open(path, "w") as output_file:
            output_file.write("text,start,duration,end\n")


_pd.DataFrame = _FakeDataFrame

_gs_mod = types.ModuleType("youtube_extension.services.ai.gemini_service")


class _FakeGeminiService:
    def __init__(self, *args, **kwargs):
        pass

    def is_available(self):
        return False


_gs_mod.GeminiService = _FakeGeminiService

_se_mod = types.ModuleType("youtube_extension.processors.scoring_engine")


class _FakeScoringEngine:
    def calculate_all_scores(self, video_info, transcript_dicts):
        return {"engagement_score": 0.5}

    def generate_actions(self, world_class_analysis):
        return [{"action": "review"}]


_se_mod.ScoringEngine = _FakeScoringEngine

_module_name = "_eventrelay_test_enhanced_extractor"
_spec = importlib_util.spec_from_file_location(
    _module_name,
    _SRC / "youtube_extension" / "processors" / "enhanced_extractor.py",
)
_extractor_mod = importlib_util.module_from_spec(_spec)  # type: ignore[arg-type]
_dependency_stubs = {
    "googleapiclient": _gcapi,
    "googleapiclient.discovery": _gcapi.discovery,
    "googleapiclient.errors": _gcapi.errors,
    "torch": types.ModuleType("torch"),
    "transformers": _tr,
    "openai": _openai_stub,
    "pandas": _pd,
    "youtube_extension.services.ai.gemini_service": _gs_mod,
    "youtube_extension.processors.scoring_engine": _se_mod,
    _module_name: _extractor_mod,
}
with patch.dict(sys.modules, _dependency_stubs):
    _spec.loader.exec_module(_extractor_mod)  # type: ignore[union-attr]

EnhancedVideoExtractor = _extractor_mod.EnhancedVideoExtractor
ProcessingStage = _extractor_mod.ProcessingStage
TranscriptSegment = _extractor_mod.TranscriptSegment
VideoContent = _extractor_mod.VideoContent
VideoMetadata = _extractor_mod.VideoMetadata
VideoSource = _extractor_mod.VideoSource

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_metadata(**kwargs) -> VideoMetadata:
    defaults = dict(
        video_id="abc123",
        title="Test Video",
        description="A test description",
        duration=120,
        upload_date="2024-01-01T00:00:00Z",
        uploader="TestChannel",
        view_count=1000,
        like_count=50,
        comment_count=10,
        tags=["python", "test"],
        thumbnail_url="https://img.youtube.com/vi/abc123/hqdefault.jpg",
        language="en",
        source=VideoSource.YOUTUBE,
    )
    defaults.update(kwargs)
    return VideoMetadata(**defaults)


def _make_segments(n: int = 3) -> list[TranscriptSegment]:
    return [
        TranscriptSegment(text=f"Segment {i}", start=float(i * 5), duration=5.0)
        for i in range(n)
    ]


def _make_content(**kwargs) -> VideoContent:
    meta = _make_metadata()
    segments = _make_segments()
    defaults = dict(
        metadata=meta,
        transcript=segments,
        summary="A brief summary.",
        key_points=["Important point one", "Key insight two"],
        topics=["python", "testing"],
        sentiment="positive",
        processing_stage=ProcessingStage.COMPLETE,
        processing_time=1.23,
    )
    defaults.update(kwargs)
    return VideoContent(**defaults)


# ===========================================================================
# VideoSource Enum
# ===========================================================================


class TestVideoSourceEnum:
    def test_values_exist(self):
        assert VideoSource.YOUTUBE.value == "youtube"
        assert VideoSource.VIMEO.value == "vimeo"
        assert VideoSource.LOCAL_FILE.value == "local"
        assert VideoSource.URL.value == "url"

    def test_member_count(self):
        assert len(VideoSource) == 4


# ===========================================================================
# ProcessingStage Enum
# ===========================================================================


class TestProcessingStageEnum:
    def test_values_exist(self):
        assert ProcessingStage.EXTRACTION.value == "extraction"
        assert ProcessingStage.TRANSCRIPTION.value == "transcription"
        assert ProcessingStage.ANALYSIS.value == "analysis"
        assert ProcessingStage.TRANSFER.value == "transfer"
        assert ProcessingStage.COMPLETE.value == "complete"

    def test_member_count(self):
        assert len(ProcessingStage) == 5


# ===========================================================================
# VideoMetadata dataclass
# ===========================================================================


class TestVideoMetadata:
    def test_required_fields(self):
        m = VideoMetadata(
            video_id="v1",
            title="Title",
            description="Desc",
            duration=60,
            upload_date="2024-01-01",
            uploader="Chan",
            view_count=100,
        )
        assert m.video_id == "v1"
        assert m.duration == 60
        assert m.source == VideoSource.YOUTUBE  # default

    def test_optional_defaults(self):
        m = _make_metadata()
        assert m.like_count == 50
        assert m.comment_count == 10
        assert m.tags == ["python", "test"]
        assert m.language == "en"

    def test_source_field(self):
        m = _make_metadata(source=VideoSource.VIMEO)
        assert m.source == VideoSource.VIMEO

    def test_thumbnail_default_empty_string(self):
        m = VideoMetadata(
            video_id="v",
            title="T",
            description="",
            duration=0,
            upload_date="",
            uploader="",
            view_count=0,
        )
        assert m.thumbnail_url == ""


# ===========================================================================
# TranscriptSegment dataclass
# ===========================================================================


class TestTranscriptSegment:
    def test_end_auto_calculated(self):
        seg = TranscriptSegment(text="Hello", start=10.0, duration=5.0)
        assert seg.end == 15.0

    def test_end_explicit(self):
        seg = TranscriptSegment(text="Hello", start=10.0, duration=5.0, end=20.0)
        assert seg.end == 20.0  # explicit wins

    def test_end_zero_start(self):
        seg = TranscriptSegment(text="Start", start=0.0, duration=3.5)
        assert seg.end == pytest.approx(3.5)

    def test_text_preserved(self):
        seg = TranscriptSegment(text="  some text  ", start=1.0, duration=2.0)
        assert seg.text == "  some text  "

    def test_end_none_triggers_post_init(self):
        seg = TranscriptSegment(text="x", start=7.0, duration=1.0, end=None)
        assert seg.end == 8.0


# ===========================================================================
# VideoContent dataclass
# ===========================================================================


class TestVideoContent:
    def test_defaults(self):
        content = VideoContent(metadata=_make_metadata(), transcript=[])
        assert content.summary is None
        assert content.key_points is None
        assert content.topics is None
        assert content.sentiment is None
        assert content.processing_stage == ProcessingStage.EXTRACTION
        assert content.processing_time == 0.0
        assert content.error_log is None
        assert content.world_class_analysis is None
        assert content.actions is None

    def test_full_content(self):
        content = _make_content()
        assert content.metadata.video_id == "abc123"
        assert len(content.transcript) == 3
        assert content.summary == "A brief summary."
        assert content.processing_stage == ProcessingStage.COMPLETE


# ===========================================================================
# EnhancedVideoExtractor.__init__
# ===========================================================================


class TestEnhancedVideoExtractorInit:
    def test_default_init(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        assert extractor.config == {}
        assert extractor.youtube is None
        assert extractor.summarizer is None
        assert extractor.sentiment_analyzer is None

    def test_config_dict_applied(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor({"openai_api_key": "sk-test"})
        assert extractor.openai_api_key == "sk-test"

    def test_env_var_openai_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        assert extractor.openai_api_key == "env-key"

    def test_config_key_overrides_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor({"openai_api_key": "config-key"})
        assert extractor.openai_api_key == "config-key"

    def test_gemini_service_none_when_unavailable(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        # HAS_GEMINI is True but FakeGeminiService always sets is_available=False
        # Either None (if __init__ raised) or FakeGeminiService instance
        # The module-level flag means gemini_service is set but may be None on error
        assert extractor.gemini_service is None or hasattr(
            extractor.gemini_service, "is_available"
        )

    def test_scoring_engine_initialized(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        assert extractor.scoring_engine is not None

    def test_youtube_none_without_api_key(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor({})
        assert extractor.youtube is None


# ===========================================================================
# _extract_summary_from_markdown
# ===========================================================================


class TestExtractSummaryFromMarkdown:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_extracts_summary_section(self):
        md = "## 🎯 Content Summary\nThis is the summary text.\n## Next Section\nother content"
        result = self.extractor._extract_summary_from_markdown(md)
        assert result == "This is the summary text."

    def test_multiline_summary(self):
        md = "## 🎯 Content Summary\nLine one.\nLine two.\n## Next Section"
        result = self.extractor._extract_summary_from_markdown(md)
        assert "Line one." in result
        assert "Line two." in result

    def test_fallback_to_first_200_chars(self):
        md = "No matching section here at all. " + "x" * 300
        result = self.extractor._extract_summary_from_markdown(md)
        assert len(result) <= 200

    def test_empty_string_returns_empty_or_truncated(self):
        result = self.extractor._extract_summary_from_markdown("")
        assert result == ""

    def test_strips_whitespace(self):
        md = "## 🎯 Content Summary\n   padded   \n## Section"
        result = self.extractor._extract_summary_from_markdown(md)
        assert result == "padded"


# ===========================================================================
# _extract_topics_from_markdown
# ===========================================================================


class TestExtractTopicsFromMarkdown:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_extracts_topics_list(self):
        md = "## 🔗 Related Topics\npython, testing, automation"
        result = self.extractor._extract_topics_from_markdown(md)
        assert "python" in result
        assert "testing" in result

    def test_no_section_returns_empty_list(self):
        md = "## Some Other Section\ncontent"
        result = self.extractor._extract_topics_from_markdown(md)
        assert result == []

    def test_cleans_brackets(self):
        md = "## 🔗 Related Topics\n['machine learning', 'AI', 'data science']"
        result = self.extractor._extract_topics_from_markdown(md)
        # Brackets stripped; topics should contain the words
        joined = " ".join(result)
        assert "machine learning" in joined or "machine" in joined

    def test_empty_section(self):
        md = "## 🔗 Related Topics\n"
        result = self.extractor._extract_topics_from_markdown(md)
        # Should return list with one empty string or empty list
        assert isinstance(result, list)


# ===========================================================================
# _extract_key_points
# ===========================================================================


class TestExtractKeyPoints:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_extracts_sentences_with_indicators(self):
        text = (
            "This is an important concept to understand. "
            "The key feature is performance. "
            "Just some random text without indicators."
        )
        result = self.extractor._extract_key_points(text)
        assert any("important" in p.lower() or "key" in p.lower() for p in result)

    def test_returns_at_most_five(self):
        # Create many matching sentences
        text = ". ".join(
            [
                f"This is an important point number {i} that explains something essential"
                for i in range(10)
            ]
        )
        result = self.extractor._extract_key_points(text)
        assert len(result) <= 5

    def test_short_sentences_excluded(self):
        text = "Key. Important. Crucial."
        result = self.extractor._extract_key_points(text)
        # Sentences < 20 chars should not appear
        for p in result:
            assert len(p) > 20

    def test_no_indicators_returns_empty(self):
        text = "Hello world. The cat sat on the mat. Nothing here."
        result = self.extractor._extract_key_points(text)
        assert result == []

    def test_returns_list_type(self):
        result = self.extractor._extract_key_points("")
        assert isinstance(result, list)


# ===========================================================================
# _extract_topics
# ===========================================================================


class TestExtractTopics:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_returns_list(self):
        result = self.extractor._extract_topics("machine learning is great")
        assert isinstance(result, list)

    def test_returns_at_most_ten(self):
        text = " ".join([f"topic{i}word" for i in range(20)])
        result = self.extractor._extract_topics(text)
        assert len(result) <= 10

    def test_stop_words_excluded(self):
        text = "this that with have from they been were said"
        result = self.extractor._extract_topics(text)
        for topic in result:
            assert topic not in {
                "this",
                "that",
                "with",
                "have",
                "from",
                "they",
                "been",
                "were",
                "said",
            }

    def test_short_words_filtered(self):
        # Words of 4 chars or fewer are filtered by the regex `[a-zA-Z]{4,}`
        text = "cat dog bird elephant python"
        result = self.extractor._extract_topics(text)
        # 'cat', 'dog' (3 chars) excluded; 'bird' (4 chars) included; 'elephant', 'python' included
        assert "elephant" in result or "python" in result

    def test_frequency_sorted(self):
        text = "python python python java java rust"
        result = self.extractor._extract_topics(text)
        assert result[0] == "python"

    def test_empty_text(self):
        result = self.extractor._extract_topics("")
        assert result == []


# ===========================================================================
# _construct_gemini_prompt
# ===========================================================================


class TestConstructGeminiPrompt:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_returns_string(self):
        result = self.extractor._construct_gemini_prompt("some text")
        assert isinstance(result, str)

    def test_contains_transcript_text(self):
        result = self.extractor._construct_gemini_prompt("my transcript content")
        assert "my transcript content" in result

    def test_contains_section_headers(self):
        result = self.extractor._construct_gemini_prompt("text")
        assert "Content Summary" in result
        assert "Key Concepts" in result
        assert "Technical Details" in result

    def test_truncates_long_text(self):
        long_text = "word " * 10000  # ~50k chars
        result = self.extractor._construct_gemini_prompt(long_text)
        # Only first 25000 chars of transcript included
        assert len(result) < len(long_text) + 1000  # prompt overhead

    def test_prompt_includes_markdown_instruction(self):
        result = self.extractor._construct_gemini_prompt("x")
        assert "Markdown" in result or "markdown" in result


# ===========================================================================
# _generate_markdown
# ===========================================================================


class TestGenerateMarkdown:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_returns_string(self):
        content = _make_content()
        result = self.extractor._generate_markdown(content)
        assert isinstance(result, str)

    def test_contains_title(self):
        content = _make_content()
        result = self.extractor._generate_markdown(content)
        assert "Test Video" in result

    def test_contains_video_id(self):
        content = _make_content()
        result = self.extractor._generate_markdown(content)
        assert "abc123" in result

    def test_contains_uploader(self):
        content = _make_content()
        result = self.extractor._generate_markdown(content)
        assert "TestChannel" in result

    def test_contains_summary(self):
        content = _make_content(summary="My custom summary")
        result = self.extractor._generate_markdown(content)
        assert "My custom summary" in result

    def test_no_summary_shows_placeholder(self):
        content = _make_content(summary=None)
        result = self.extractor._generate_markdown(content)
        assert "No summary available" in result

    def test_key_points_listed(self):
        content = _make_content(key_points=["Point Alpha", "Point Beta"])
        result = self.extractor._generate_markdown(content)
        assert "Point Alpha" in result
        assert "Point Beta" in result

    def test_no_key_points_message(self):
        content = _make_content(key_points=None)
        result = self.extractor._generate_markdown(content)
        assert "No key points extracted" in result

    def test_topics_joined(self):
        content = _make_content(topics=["python", "testing"])
        result = self.extractor._generate_markdown(content)
        assert "python" in result
        assert "testing" in result

    def test_no_topics_message(self):
        content = _make_content(topics=None)
        result = self.extractor._generate_markdown(content)
        assert "No topics identified" in result

    def test_sentiment_shown(self):
        content = _make_content(sentiment="positive")
        result = self.extractor._generate_markdown(content)
        assert "positive" in result

    def test_transcript_timestamps(self):
        segments = [
            TranscriptSegment(text="Hello world", start=0.0, duration=5.0),
            TranscriptSegment(text="Second segment", start=65.0, duration=5.0),
        ]
        content = _make_content(transcript=segments)
        result = self.extractor._generate_markdown(content)
        assert "0:00" in result
        assert "1:05" in result

    def test_empty_transcript(self):
        content = _make_content(transcript=[])
        result = self.extractor._generate_markdown(content)
        assert "## Transcript" in result

    def test_duration_formatted(self):
        # duration=120 → 2:00
        content = _make_content()
        result = self.extractor._generate_markdown(content)
        assert "2:00" in result


# ===========================================================================
# export_content - JSON
# ===========================================================================


class TestExportContentJSON:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_json_export_creates_file(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "output")
        result_path = self.extractor.export_content(content, "json", out_base)
        assert result_path == out_base + ".json"
        assert Path(result_path).exists()

    def test_json_export_valid_json(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "output")
        result_path = self.extractor.export_content(content, "json", out_base)
        with open(result_path) as f:
            data = json.load(f)
        assert data["metadata"]["video_id"] == "abc123"

    def test_json_contains_transcript(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "out")
        result_path = self.extractor.export_content(content, "json", out_base)
        with open(result_path) as f:
            data = json.load(f)
        assert len(data["transcript"]) == 3

    def test_json_format_case_insensitive(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "out")
        result_path = self.extractor.export_content(content, "JSON", out_base)
        assert result_path.endswith(".json")
        assert Path(result_path).exists()


# ===========================================================================
# export_content - Markdown
# ===========================================================================


class TestExportContentMarkdown:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_markdown_export_creates_file(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "output")
        result_path = self.extractor.export_content(content, "markdown", out_base)
        assert result_path == out_base + ".md"
        assert Path(result_path).exists()

    def test_markdown_content_has_title(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "out")
        result_path = self.extractor.export_content(content, "markdown", out_base)
        text = Path(result_path).read_text()
        assert "Test Video" in text

    def test_markdown_case_insensitive(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "out")
        result_path = self.extractor.export_content(content, "Markdown", out_base)
        assert result_path.endswith(".md")


# ===========================================================================
# export_content - CSV
# ===========================================================================


class TestExportContentCSV:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_csv_export_creates_file(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "output")
        result_path = self.extractor.export_content(content, "csv", out_base)
        assert result_path == out_base + ".csv"
        assert Path(result_path).exists()


# ===========================================================================
# export_content - auto-generated path
# ===========================================================================


class TestExportContentAutoPath:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_auto_path_uses_video_id(self, tmp_path, monkeypatch):
        # Change cwd so auto-generated file lands in tmp_path
        monkeypatch.chdir(tmp_path)
        content = _make_content()
        result_path = self.extractor.export_content(content, "json")
        assert "abc123" in result_path
        assert Path(result_path).exists()
        Path(result_path).unlink()  # cleanup


# ===========================================================================
# export_content - unsupported format
# ===========================================================================


class TestExportContentUnsupportedFormat:
    def setup_method(self):
        self.extractor = EnhancedVideoExtractor()

    def test_raises_on_unknown_format(self, tmp_path):
        content = _make_content()
        out_base = str(tmp_path / "out")
        with pytest.raises(ValueError, match="Unsupported format"):
            self.extractor.export_content(content, "xml", out_base)


# ===========================================================================
# extract_video_metadata
# ===========================================================================


class TestExtractVideoMetadata:
    async def test_raises_when_youtube_api_not_set(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        # youtube is None, no api key
        with pytest.raises(ValueError, match="API key"):
            await extractor.extract_video_metadata("abc123")

    async def test_raises_when_no_youtube_client_but_has_key(self, monkeypatch):
        monkeypatch.setenv("YOUTUBE_API_KEY", "fake-key")
        extractor = EnhancedVideoExtractor()
        # youtube is still None because build() is not mocked to work
        # It either raises ValueError or another error about YouTube API
        with pytest.raises(ValueError):
            await extractor.extract_video_metadata("abc123")

    async def test_returns_metadata_from_mocked_youtube(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        # Build a fake YouTube client
        fake_response = {
            "items": [
                {
                    "snippet": {
                        "title": "My Video",
                        "description": "A great video",
                        "publishedAt": "2024-01-01T00:00:00Z",
                        "channelTitle": "MyChan",
                        "tags": ["a", "b"],
                        "thumbnails": {"high": {"url": "http://img"}},
                        "defaultLanguage": "en",
                    },
                    "statistics": {
                        "viewCount": "5000",
                        "likeCount": "200",
                        "commentCount": "50",
                    },
                    "contentDetails": {"duration": "PT10M30S"},
                }
            ]
        }

        mock_videos = MagicMock()
        mock_videos.return_value.list.return_value.execute.return_value = fake_response
        extractor.youtube = MagicMock()
        extractor.youtube.videos = mock_videos

        meta = await extractor.extract_video_metadata("testvid123")
        assert meta.title == "My Video"
        assert meta.uploader == "MyChan"
        assert meta.view_count == 5000
        assert meta.like_count == 200
        assert meta.duration == 630  # 10*60 + 30

    async def test_raises_when_video_not_found(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        fake_response = {"items": []}
        mock_videos = MagicMock()
        mock_videos.return_value.list.return_value.execute.return_value = fake_response
        extractor.youtube = MagicMock()
        extractor.youtube.videos = mock_videos

        with pytest.raises(ValueError, match="not found"):
            await extractor.extract_video_metadata("missingvid")


# ===========================================================================
# analyze_content
# ===========================================================================


class TestAnalyzeContent:
    async def test_returns_dict(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        extractor.gemini_service = None
        extractor.summarizer = None
        extractor.sentiment_analyzer = None
        segments = _make_segments(2)
        result = await extractor.analyze_content(segments)
        assert isinstance(result, dict)

    async def test_uses_gemini_when_available(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        mock_gemini = MagicMock()
        mock_gemini.is_available.return_value = True
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.response = (
            "## 🎯 Content Summary\nGreat summary.\n## 🔗 Related Topics\npython, ai"
        )
        mock_gemini.process_text = AsyncMock(return_value=mock_result)
        extractor.gemini_service = mock_gemini

        segments = _make_segments(3)
        result = await extractor.analyze_content(segments)

        assert "summary" in result
        assert result["summary"] == "Great summary."
        assert "sentiment" in result
        assert "topics" in result

    async def test_gemini_failure_falls_back(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        mock_gemini = MagicMock()
        mock_gemini.is_available.return_value = True
        mock_gemini.process_text = AsyncMock(side_effect=RuntimeError("Gemini down"))
        extractor.gemini_service = mock_gemini
        extractor.summarizer = None
        extractor.sentiment_analyzer = None

        segments = _make_segments(2)
        result = await extractor.analyze_content(segments)
        # Falls back gracefully; no exception
        assert isinstance(result, dict)

    async def test_with_summarizer_and_sentiment(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        extractor.gemini_service = None

        # Stub local AI
        fake_summarizer = MagicMock(return_value=[{"summary_text": "Local summary"}])
        fake_sentiment = MagicMock(
            return_value=[{"label": "POSITIVE", "score": 0.95}]
        )
        extractor.summarizer = fake_summarizer
        extractor.sentiment_analyzer = fake_sentiment

        # Create a long enough transcript
        long_segments = [
            TranscriptSegment(
                text="This is a very important segment about Python programming. " * 10,
                start=float(i),
                duration=1.0,
            )
            for i in range(20)
        ]
        result = await extractor.analyze_content(long_segments)
        assert result.get("summary") == "Local summary"
        assert result.get("sentiment") == "positive"
        assert result.get("sentiment_score") == pytest.approx(0.95)

    async def test_short_text_no_summarizer_called(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        extractor.gemini_service = None

        fake_summarizer = MagicMock(return_value=[{"summary_text": "Should not appear"}])
        fake_sentiment = MagicMock(
            return_value=[{"label": "NEGATIVE", "score": 0.8}]
        )
        extractor.summarizer = fake_summarizer
        extractor.sentiment_analyzer = fake_sentiment

        # Text shorter than 1000 chars, summarizer should not be called
        short_segments = [TranscriptSegment(text="Short text.", start=0.0, duration=1.0)]
        result = await extractor.analyze_content(short_segments)
        fake_summarizer.assert_not_called()
        assert result.get("summary") == "Short text."

    async def test_gemini_result_not_success_falls_back(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        mock_gemini = MagicMock()
        mock_gemini.is_available.return_value = True
        mock_result = MagicMock()
        mock_result.success = False
        mock_result.response = None
        mock_gemini.process_text = AsyncMock(return_value=mock_result)
        extractor.gemini_service = mock_gemini
        extractor.summarizer = None
        extractor.sentiment_analyzer = None

        segments = _make_segments(2)
        result = await extractor.analyze_content(segments)
        assert isinstance(result, dict)


# ===========================================================================
# extract_transcript
# ===========================================================================


class TestExtractTranscript:
    async def test_raises_when_no_video_deps(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        orig = _extractor_mod.HAS_VIDEO_DEPS
        try:
            _extractor_mod.HAS_VIDEO_DEPS = False
            extractor = EnhancedVideoExtractor()
            with pytest.raises(ValueError, match="Video dependencies not available"):
                await extractor.extract_transcript("abc123")
        finally:
            _extractor_mod.HAS_VIDEO_DEPS = orig

    async def test_successful_transcript_extraction(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        orig = _extractor_mod.HAS_VIDEO_DEPS
        try:
            _extractor_mod.HAS_VIDEO_DEPS = True
            extractor = EnhancedVideoExtractor()

            fake_response_data = {
                "success": True,
                "data": {
                    "subtitles": [
                        {"text": "Hello", "start": "0.0", "dur": "2.0"},
                        {"text": "World", "start": "2.0", "dur": "3.0"},
                    ]
                },
            }

            mock_response = MagicMock()
            mock_response.json.return_value = fake_response_data
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch.object(
                _extractor_mod.httpx,
                "AsyncClient",
                return_value=mock_client,
            ):
                segments = await extractor.extract_transcript("abc123")

            assert len(segments) == 2
            assert segments[0].text == "Hello"
            assert segments[0].start == 0.0
            assert segments[1].text == "World"
        finally:
            _extractor_mod.HAS_VIDEO_DEPS = orig

    async def test_http_request_error_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        orig = _extractor_mod.HAS_VIDEO_DEPS
        try:
            _extractor_mod.HAS_VIDEO_DEPS = True
            extractor = EnhancedVideoExtractor()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=_extractor_mod.httpx.RequestError("Connection refused")
            )

            with patch.object(
                _extractor_mod.httpx,
                "AsyncClient",
                return_value=mock_client,
            ):
                with pytest.raises(ValueError, match="caption extractor service"):
                    await extractor.extract_transcript("abc123")
        finally:
            _extractor_mod.HAS_VIDEO_DEPS = orig

    async def test_failed_success_flag_raises(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        orig = _extractor_mod.HAS_VIDEO_DEPS
        try:
            _extractor_mod.HAS_VIDEO_DEPS = True
            extractor = EnhancedVideoExtractor()

            fake_response_data = {"success": False, "error": "Video unavailable"}

            mock_response = MagicMock()
            mock_response.json.return_value = fake_response_data
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)

            with patch.object(
                _extractor_mod.httpx,
                "AsyncClient",
                return_value=mock_client,
            ):
                with pytest.raises(Exception):
                    await extractor.extract_transcript("abc123")
        finally:
            _extractor_mod.HAS_VIDEO_DEPS = orig


# ===========================================================================
# batch_process_videos
# ===========================================================================


class TestBatchProcessVideos:
    async def test_batch_returns_list(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        # Mock process_video to return a simple content
        async def mock_process(url):
            return _make_content()

        extractor.process_video = mock_process

        results = await extractor.batch_process_videos(
            ["https://youtube.com/watch?v=abc", "https://youtube.com/watch?v=def"]
        )
        assert len(results) == 2

    async def test_batch_handles_exceptions(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        call_count = 0

        async def mock_process(url):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Processing error")
            return _make_content()

        extractor.process_video = mock_process

        results = await extractor.batch_process_videos(
            ["https://youtube.com/watch?v=bad", "https://youtube.com/watch?v=good"]
        )
        assert len(results) == 2
        # First result should be an error VideoContent
        assert results[0].error_log is not None
        assert len(results[0].error_log) > 0

    async def test_batch_empty_list(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()
        results = await extractor.batch_process_videos([])
        assert results == []


# ===========================================================================
# process_video integration (mocked sub-methods)
# ===========================================================================


class TestProcessVideo:
    # Use a proper 11-char video ID in the URL for these tests
    _VALID_URL = "https://www.youtube.com/watch?v=abc12345678"
    _VALID_VID = "abc12345678"

    async def test_process_video_success(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        meta = _make_metadata(video_id=self._VALID_VID)
        segs = _make_segments(3)
        analysis = {"summary": "Good video", "topics": ["python"], "key_points": []}

        extractor.extract_video_metadata = AsyncMock(return_value=meta)
        extractor.extract_transcript = AsyncMock(return_value=segs)
        extractor.analyze_content = AsyncMock(return_value=analysis)

        content = await extractor.process_video(self._VALID_URL)

        assert content.metadata.video_id == self._VALID_VID
        assert content.processing_stage == ProcessingStage.COMPLETE
        assert content.summary == "Good video"
        assert len(content.transcript) == 3

    async def test_process_video_invalid_url(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        # patch extract_video_id to return None so video_id is assigned (None)
        with patch.object(_extractor_mod, "extract_video_id", return_value=None):
            content = await extractor.process_video("not-a-youtube-url")

        # Should return error content
        assert content.error_log is not None
        assert content.processing_stage == ProcessingStage.EXTRACTION

    async def test_process_video_metadata_failure_returns_error_content(
        self, monkeypatch
    ):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        meta = _make_metadata(video_id=self._VALID_VID)
        extractor.extract_video_metadata = AsyncMock(
            side_effect=ValueError("API error")
        )

        content = await extractor.process_video(self._VALID_URL)

        assert content.error_log is not None
        assert "API error" in content.error_log[0]
        assert content.processing_stage == ProcessingStage.EXTRACTION

    async def test_process_video_scoring_applied(self, monkeypatch):
        monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
        extractor = EnhancedVideoExtractor()

        meta = _make_metadata(video_id=self._VALID_VID)
        segs = _make_segments(3)
        analysis = {"summary": "Summary", "topics": [], "key_points": []}

        extractor.extract_video_metadata = AsyncMock(return_value=meta)
        extractor.extract_transcript = AsyncMock(return_value=segs)
        extractor.analyze_content = AsyncMock(return_value=analysis)

        content = await extractor.process_video(self._VALID_URL)

        # Scoring engine should have been called
        assert content.world_class_analysis is not None
        assert content.actions is not None
