"""
Tests for Temporal Video Analysis
---------------------------------
Tests timestamp-based analysis and temporal reasoning.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.integration.temporal_video_analysis import (
    TemporalEvent,
    TemporalSegment,
    TemporalVideoAnalyzer,
)


@pytest.fixture
def mock_gemini_service():
    """Create a mock Gemini service (module-level so every test class can use it)."""
    with patch("src.integration.temporal_video_analysis.GeminiVideoService") as mock:
        service = MagicMock()
        service.analyze_video = AsyncMock()
        service.answer_video_question = AsyncMock()
        service.close = AsyncMock()
        mock.return_value = service
        yield service


class TestTemporalSegment:
    """Test temporal segment utilities."""

    def test_segment_creation(self):
        """Test creating a temporal segment."""
        segment = TemporalSegment(
            start_time="1:30",
            end_time="3:45",
            description="Code demo section"
        )

        assert segment.start_time == "1:30"
        assert segment.end_time == "3:45"
        assert segment.description == "Code demo section"

    def test_timestamp_to_seconds(self):
        """Test timestamp conversion."""
        segment = TemporalSegment(start_time="0:00", end_time="1:00")

        assert segment.to_seconds("1:30") == 90
        assert segment.to_seconds("0:45") == 45
        assert segment.to_seconds("1:00:30") == 3630

    def test_duration_calculation(self):
        """Test segment duration calculation."""
        segment = TemporalSegment(
            start_time="1:30",
            end_time="3:45"
        )

        # 3:45 - 1:30 = 2:15 = 135 seconds
        assert segment.duration_seconds == 135


class TestTemporalEvent:
    """Test temporal event structure."""

    def test_event_creation(self):
        """Test creating a temporal event."""
        event = TemporalEvent(
            timestamp="2:30",
            event_type="code_change",
            description="API endpoint modified",
            confidence=0.95,
            metadata={"file": "api.py"}
        )

        assert event.timestamp == "2:30"
        assert event.event_type == "code_change"
        assert event.description == "API endpoint modified"
        assert event.confidence == 0.95
        assert event.metadata["file"] == "api.py"


class TestTemporalVideoAnalyzer:
    """Test temporal video analysis capabilities."""

    @pytest.mark.asyncio
    async def test_analyze_segment(self, mock_gemini_service):
        """Test analyzing a video segment."""
        # Mock response
        mock_response = MagicMock()
        mock_response.summary = "Code demonstration in this segment"
        mock_response.key_events = [{"event": "Function defined", "timestamp": "2:00"}]
        mock_response.timestamps = [{"timestamp": "2:00", "event": "Function defined"}]
        mock_gemini_service.analyze_video.return_value = mock_response

        analyzer = TemporalVideoAnalyzer()
        result = await analyzer.analyze_segment(
            video_url="https://youtube.com/watch?v=example",
            start_time="1:30",
            end_time="3:00",
            focus="code"
        )

        assert result.summary == "Code demonstration in this segment"
        assert len(result.key_events) > 0

        # Verify the call included temporal context
        call_args = mock_gemini_service.analyze_video.call_args
        assert "1:30" in call_args[0][1]  # Prompt includes start time
        assert "3:00" in call_args[0][1]  # Prompt includes end time

        await analyzer.close()

    @pytest.mark.asyncio
    async def test_extract_temporal_events(self, mock_gemini_service):
        """Test extracting timestamped events."""
        # Mock JSON response with events
        mock_response = MagicMock()
        mock_response.summary = json.dumps({
            "events": [
                {
                    "timestamp": "1:00",
                    "type": "code_change",
                    "description": "Function added",
                    "confidence": 0.95,
                    "metadata": {}
                },
                {
                    "timestamp": "2:30",
                    "type": "api_call",
                    "description": "HTTP request made",
                    "confidence": 0.88,
                    "metadata": {"endpoint": "/api/users"}
                }
            ]
        })
        mock_response.key_events = []
        mock_gemini_service.analyze_video.return_value = mock_response

        analyzer = TemporalVideoAnalyzer()
        events = await analyzer.extract_temporal_events(
            video_url="https://youtube.com/watch?v=example",
            event_types=["code_change", "api_call"]
        )

        assert len(events) == 2
        assert events[0].timestamp == "1:00"
        assert events[0].event_type == "code_change"
        assert events[1].timestamp == "2:30"
        assert events[1].event_type == "api_call"

        await analyzer.close()

    @pytest.mark.asyncio
    async def test_temporal_question(self, mock_gemini_service):
        """Test temporal question answering."""
        mock_gemini_service.answer_video_question.return_value = (
            "Answer: The API is called at 2:30\nEvidence at 2:30: HTTP POST request visible"
        )

        analyzer = TemporalVideoAnalyzer()
        answer = await analyzer.temporal_question(
            video_url="https://youtube.com/watch?v=example",
            question="When is the API called?",
            time_context="between 2:00 and 3:00"
        )

        assert "2:30" in answer
        assert "API" in answer

        # Verify temporal context was included
        call_args = mock_gemini_service.answer_video_question.call_args
        prompt = call_args[0][1]
        assert "between 2:00 and 3:00" in prompt

        await analyzer.close()

    @pytest.mark.asyncio
    async def test_create_timeline(self, mock_gemini_service):
        """Test creating video timeline."""
        # Mock timeline response
        mock_response = MagicMock()
        mock_response.summary = json.dumps({
            "timeline": [
                {
                    "timestamp": "0:00",
                    "section_title": "Introduction",
                    "description": "Overview of the topic"
                },
                {
                    "timestamp": "2:00",
                    "section_title": "Code Demo",
                    "description": "Live coding demonstration"
                },
                {
                    "timestamp": "5:00",
                    "section_title": "Testing",
                    "description": "Running tests"
                }
            ]
        })
        mock_response.key_events = []
        mock_gemini_service.analyze_video.return_value = mock_response

        analyzer = TemporalVideoAnalyzer()
        timeline = await analyzer.create_timeline(
            video_url="https://youtube.com/watch?v=example",
            granularity="medium"
        )

        assert len(timeline) == 3
        assert timeline[0]["section_title"] == "Introduction"
        assert timeline[1]["section_title"] == "Code Demo"
        assert timeline[2]["section_title"] == "Testing"

        await analyzer.close()

    @pytest.mark.asyncio
    async def test_compare_segments(self, mock_gemini_service):
        """Test comparing multiple segments."""
        # Mock comparison response
        mock_response = MagicMock()
        mock_response.summary = json.dumps({
            "segments_analyzed": 2,
            "comparisons": [
                {
                    "aspect": "Code quality",
                    "segment_1": "Good error handling",
                    "segment_2": "Lacks error handling",
                    "difference": "First segment is more robust"
                }
            ]
        })
        mock_response.key_events = []
        mock_gemini_service.analyze_video.return_value = mock_response

        analyzer = TemporalVideoAnalyzer()
        comparison = await analyzer.compare_segments(
            video_url="https://youtube.com/watch?v=example",
            segments=[("1:00", "2:00"), ("3:00", "4:00")],
            comparison_focus="code quality"
        )

        assert comparison["segments_analyzed"] == 2
        assert len(comparison["comparisons"]) > 0

        await analyzer.close()

    @pytest.mark.asyncio
    async def test_extract_tutorial_steps(self, mock_gemini_service):
        """Test extracting tutorial steps."""
        # Mock tutorial steps response
        mock_response = MagicMock()
        mock_response.summary = json.dumps({
            "tutorial_title": "Build a REST API",
            "steps": [
                {
                    "step_number": 1,
                    "timestamp": "0:30",
                    "title": "Setup project",
                    "instructions": "Initialize Node.js project",
                    "code_snippets": ["npm init -y"]
                },
                {
                    "step_number": 2,
                    "timestamp": "2:00",
                    "title": "Install dependencies",
                    "instructions": "Install Express and other packages",
                    "code_snippets": ["npm install express"]
                }
            ]
        })
        mock_response.key_events = []
        mock_gemini_service.analyze_video.return_value = mock_response

        analyzer = TemporalVideoAnalyzer()
        steps = await analyzer.extract_tutorial_steps(
            video_url="https://youtube.com/watch?v=example"
        )

        assert len(steps) == 2
        assert steps[0]["step_number"] == 1
        assert steps[0]["title"] == "Setup project"
        assert steps[1]["step_number"] == 2
        assert steps[1]["title"] == "Install dependencies"

        await analyzer.close()


class TestTemporalAnalysisIntegration:
    """Integration tests for temporal analysis."""

    @pytest.mark.asyncio
    async def test_segment_to_events_workflow(self, mock_gemini_service):
        """Test workflow from segment analysis to event extraction."""
        # Mock segment analysis
        segment_response = MagicMock()
        segment_response.summary = "Code section with API calls"
        segment_response.key_events = []

        # Mock events extraction
        events_response = MagicMock()
        events_response.summary = json.dumps({
            "events": [
                {
                    "timestamp": "1:30",
                    "type": "api_call",
                    "description": "GET /api/users",
                    "confidence": 0.9
                }
            ]
        })
        events_response.key_events = []

        mock_gemini_service.analyze_video.side_effect = [
            segment_response,
            events_response
        ]

        analyzer = TemporalVideoAnalyzer()

        # Analyze segment
        segment_result = await analyzer.analyze_segment(
            "https://youtube.com/watch?v=example",
            "1:00",
            "2:00"
        )

        # Extract events
        events = await analyzer.extract_temporal_events(
            "https://youtube.com/watch?v=example",
            event_types=["api_call"]
        )

        assert segment_result.summary is not None
        assert len(events) > 0

        await analyzer.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
