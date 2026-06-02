"""
Tests for src/youtube_extension/services/video_subagent.py

Covers:
- YouTubeVideoSubagent.__init__
- _analyze_content
- _generate_actions
- _create_verification_proof
- _calculate_duration
- _call_mcp_tool
- process_youtube_video
"""
from __future__ import annotations

import asyncio
import sys
import types as _types

# Stub the broken import chain that tries to load vision_processor (pyo3/cffi)
if "vision_processor" not in sys.modules:
    _vision = _types.ModuleType("vision_processor")
    _vision.get_processor = lambda: None  # type: ignore[attr-defined]
    sys.modules["vision_processor"] = _vision

if "src.agents.github_deployment_agent" not in sys.modules:
    _gda = _types.ModuleType("src.agents.github_deployment_agent")
    _gda.GitHubDeploymentAgent = None  # type: ignore[attr-defined]
    sys.modules.setdefault("src", _types.ModuleType("src"))
    sys.modules.setdefault("src.agents", _types.ModuleType("src.agents"))
    sys.modules["src.agents.github_deployment_agent"] = _gda
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

with patch("pathlib.Path.mkdir"):
    from youtube_extension.services.video_subagent import YouTubeVideoSubagent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_subagent(tmp_path: Path) -> YouTubeVideoSubagent:
    with patch("pathlib.Path.mkdir"):
        agent = YouTubeVideoSubagent()
    agent.results_dir = tmp_path
    return agent


# ===========================================================================
# __init__
# ===========================================================================

class TestInit:
    def test_has_mcp_server_path(self):
        with patch("pathlib.Path.mkdir"):
            a = YouTubeVideoSubagent()
        assert hasattr(a, "mcp_server_path")

    def test_results_dir_is_path(self):
        with patch("pathlib.Path.mkdir"):
            a = YouTubeVideoSubagent()
        assert isinstance(a.results_dir, Path)


# ===========================================================================
# _calculate_duration
# ===========================================================================

class TestCalculateDuration:
    def _agent(self) -> YouTubeVideoSubagent:
        with patch("pathlib.Path.mkdir"):
            return YouTubeVideoSubagent()

    def test_returns_seconds_string(self):
        a = self._agent()
        t1 = "2024-01-01T00:00:00"
        t2 = "2024-01-01T00:00:05"
        result = a._calculate_duration(t1, t2)
        assert "5.0" in result
        assert "seconds" in result

    def test_returns_unknown_for_bad_input(self):
        a = self._agent()
        result = a._calculate_duration("not-a-time", "also-bad")
        assert result == "unknown"

    def test_same_time_returns_zero(self):
        a = self._agent()
        t = "2024-06-01T12:00:00"
        result = a._calculate_duration(t, t)
        assert "0.0" in result


# ===========================================================================
# _analyze_content
# ===========================================================================

class TestAnalyzeContent:
    def _agent(self) -> YouTubeVideoSubagent:
        with patch("pathlib.Path.mkdir"):
            return YouTubeVideoSubagent()

    def test_empty_video_data_returns_unknown(self):
        a = self._agent()
        result = a._analyze_content({})
        assert result["content_type"] == "unknown"
        assert result["confidence"] == "low"

    def test_rickroll_title_detected(self):
        a = self._agent()
        video_data = {"metadata": {"title": "Never Gonna Give You Up - Rick Astley"}}
        result = a._analyze_content(video_data)
        assert result["content_type"] == "music/entertainment"
        assert result["confidence"] == "high"
        assert len(result["key_insights"]) > 0
        assert len(result["actionable_items"]) > 0

    def test_non_rickroll_title_stays_unknown(self):
        a = self._agent()
        video_data = {"metadata": {"title": "Python Tutorial"}}
        result = a._analyze_content(video_data)
        assert result["content_type"] == "unknown"

    def test_domain_analysis_sets_fields(self):
        a = self._agent()
        video_data = {
            "domain_analysis": {
                "primary_domain": "tech",
                "confidence": "high",
                "suggested_actions": ["action1"]
            }
        }
        result = a._analyze_content(video_data)
        assert result["detected_domain"] == "tech"
        assert result["domain_confidence"] == "high"
        assert result["suggested_domain_actions"] == ["action1"]

    def test_metadata_with_domain_analysis_combined(self):
        a = self._agent()
        video_data = {
            "metadata": {"title": "rickroll"},
            "domain_analysis": {
                "primary_domain": "entertainment",
                "confidence": "medium",
                "suggested_actions": []
            }
        }
        result = a._analyze_content(video_data)
        assert result["content_type"] == "music/entertainment"
        assert result["detected_domain"] == "entertainment"


# ===========================================================================
# _generate_actions
# ===========================================================================

class TestGenerateActions:
    def _agent(self) -> YouTubeVideoSubagent:
        with patch("pathlib.Path.mkdir"):
            return YouTubeVideoSubagent()

    def test_empty_inputs_returns_empty_list(self):
        a = self._agent()
        result = a._generate_actions({}, {})
        assert result == []

    def test_actionable_items_become_content_actions(self):
        a = self._agent()
        content_analysis = {
            "actionable_items": ["Do thing A", "Do thing B"],
            "content_type": "tech"
        }
        result = a._generate_actions({}, content_analysis)
        types = [r["type"] for r in result]
        assert all(t == "content_action" for t in types)
        assert len(result) == 2

    def test_domain_analysis_actions(self):
        a = self._agent()
        video_data = {
            "domain_analysis": {
                "suggested_actions": ["Build something"],
                "primary_domain": "tech"
            }
        }
        result = a._generate_actions(video_data, {})
        assert any(r["type"] == "domain_action" for r in result)
        assert any(r["priority"] == "high" for r in result)

    def test_transcript_adds_two_actions(self):
        a = self._agent()
        video_data = {"transcript": "Some transcript text here"}
        result = a._generate_actions(video_data, {})
        transcript_actions = [r for r in result if r["type"] == "transcript_action"]
        assert len(transcript_actions) == 2

    def test_combined_sources_produces_all_actions(self):
        a = self._agent()
        video_data = {
            "domain_analysis": {
                "suggested_actions": ["Domain action"],
                "primary_domain": "education"
            },
            "transcript": "Hello world"
        }
        content_analysis = {
            "actionable_items": ["Content action"],
            "content_type": "education"
        }
        result = a._generate_actions(video_data, content_analysis)
        types = {r["type"] for r in result}
        assert "content_action" in types
        assert "domain_action" in types
        assert "transcript_action" in types


# ===========================================================================
# _create_verification_proof
# ===========================================================================

class TestCreateVerificationProof:
    def _agent(self) -> YouTubeVideoSubagent:
        with patch("pathlib.Path.mkdir"):
            return YouTubeVideoSubagent()

    def test_empty_inputs_returns_unconfirmed(self):
        a = self._agent()
        proof = a._create_verification_proof({}, {})
        assert proof["data_extraction_confirmed"] is False
        assert proof["metadata_extracted"] is False
        assert proof["transcript_extracted"] is False
        assert proof["domain_classified"] is False

    def test_metadata_extraction_confirmed(self):
        a = self._agent()
        video_data = {"metadata": {"title": "Test", "uploader": "User", "duration": 120, "description": "Desc"}}
        proof = a._create_verification_proof(video_data, {"status": "success"})
        assert proof["metadata_extracted"] is True
        assert proof["data_extraction_confirmed"] is True
        assert proof["verification_details"]["metadata"]["title_extracted"] is True

    def test_transcript_extraction_confirmed(self):
        a = self._agent()
        video_data = {"transcript": "This is a transcript."}
        proof = a._create_verification_proof(video_data, {})
        assert proof["transcript_extracted"] is True
        assert proof["data_extraction_confirmed"] is True
        assert proof["verification_details"]["transcript"]["transcript_length"] > 0

    def test_domain_classified_confirmed(self):
        a = self._agent()
        video_data = {
            "domain_analysis": {
                "primary_domain": "tech",
                "confidence": "high",
                "suggested_actions": ["act1", "act2"]
            }
        }
        proof = a._create_verification_proof(video_data, {})
        assert proof["domain_classified"] is True
        assert proof["data_extraction_confirmed"] is True
        assert proof["verification_details"]["domain"]["actions_generated"] == 2

    def test_mcp_result_status_recorded(self):
        a = self._agent()
        proof = a._create_verification_proof({}, {"status": "success", "result": {"data": "x"}})
        assert proof["verification_details"]["mcp_tool"]["tool_status"] == "success"
        assert proof["verification_details"]["mcp_tool"]["tool_response_received"] is True

    def test_empty_metadata_dict_does_not_set_metadata_extracted(self):
        a = self._agent()
        video_data = {"metadata": {}}  # falsy empty dict
        proof = a._create_verification_proof(video_data, {})
        assert proof["metadata_extracted"] is False


# ===========================================================================
# _call_mcp_tool
# ===========================================================================

class TestCallMcpTool:
    async def test_successful_mcp_call(self, tmp_path):
        a = make_subagent(tmp_path)
        response = json.dumps({"result": {"data": "video_info"}})

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(response.encode(), b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await a._call_mcp_tool("test_tool", {"arg": "val"})

        assert result["status"] == "success"
        assert result["result"] == {"data": "video_info"}

    async def test_process_error_returns_error_status(self, tmp_path):
        a = make_subagent(tmp_path)

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"MCP server crashed"))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await a._call_mcp_tool("test_tool", {})

        assert result["status"] == "error"
        assert "MCP server error" in result["error"]

    async def test_exception_returns_error(self, tmp_path):
        a = make_subagent(tmp_path)

        with patch("asyncio.create_subprocess_exec", side_effect=OSError("no such file")):
            result = await a._call_mcp_tool("test_tool", {})

        assert result["status"] == "error"
        assert "Failed to call MCP tool" in result["error"]

    async def test_mcp_returns_error_in_response(self, tmp_path):
        a = make_subagent(tmp_path)
        response = json.dumps({"error": {"message": "Tool not found"}})

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(response.encode(), b""))

        with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
            result = await a._call_mcp_tool("missing_tool", {})

        assert result["status"] == "error"
        assert "Tool not found" in result["error"]


# ===========================================================================
# process_youtube_video
# ===========================================================================

class TestProcessYoutubeVideo:
    async def test_successful_processing(self, tmp_path):
        a = make_subagent(tmp_path)

        tool_response = {
            "status": "completed",
            "metadata": {"title": "Test", "uploader": "TestUser", "duration": 60, "description": "Test"},
            "transcript": "Hello world",
        }
        mcp_result = {"status": "success", "result": tool_response}

        a._call_mcp_tool = AsyncMock(return_value=mcp_result)
        result = await a.process_youtube_video("https://youtube.com/watch?v=test")

        assert result["status"] == "completed"
        assert result["real_data_extracted"] is True
        assert "generated_actions" in result
        assert "verification_proof" in result
        # Results file saved
        assert (tmp_path / f"{result['session_id']}_results.json").exists()

    async def test_mcp_tool_error(self, tmp_path):
        a = make_subagent(tmp_path)
        a._call_mcp_tool = AsyncMock(return_value={"status": "error", "error": "MCP failed"})

        result = await a.process_youtube_video("https://youtube.com/watch?v=test")
        assert result["status"] == "error"
        assert result["real_data_extracted"] is False

    async def test_tool_returns_failed_status(self, tmp_path):
        a = make_subagent(tmp_path)
        tool_response = {"status": "failed", "error": "Could not process video"}
        a._call_mcp_tool = AsyncMock(return_value={"status": "success", "result": tool_response})

        result = await a.process_youtube_video("https://youtube.com/watch?v=test")
        assert result["status"] == "error"

    async def test_exception_during_processing(self, tmp_path):
        a = make_subagent(tmp_path)
        a._call_mcp_tool = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        result = await a.process_youtube_video("https://youtube.com/watch?v=test")
        assert result["status"] == "error"
        assert "Unexpected error" in result["error"]

    async def test_result_file_written(self, tmp_path):
        a = make_subagent(tmp_path)
        a._call_mcp_tool = AsyncMock(return_value={"status": "error", "error": "fail"})

        result = await a.process_youtube_video("https://youtube.com/watch?v=test")
        result_file = Path(result["result_file"])
        assert result_file.exists()
        data = json.loads(result_file.read_text())
        assert data["url"] == "https://youtube.com/watch?v=test"

    async def test_processing_with_content_list_result(self, tmp_path):
        """Covers the content[0]['text'] JSON-parse branch"""
        a = make_subagent(tmp_path)
        tool_data = {
            "status": "completed",
            "metadata": {"title": "Nested", "uploader": "U", "duration": 10, "description": "D"},
        }
        result_with_content = {"content": [{"text": json.dumps(tool_data)}]}
        a._call_mcp_tool = AsyncMock(return_value={"status": "success", "result": result_with_content})

        result = await a.process_youtube_video("https://youtube.com/watch?v=nested")
        assert result["status"] == "completed"

    async def test_processing_with_transcription_field(self, tmp_path):
        """Covers the 'transcription' -> 'transcript' mapping"""
        a = make_subagent(tmp_path)
        tool_response = {
            "status": "completed",
            "transcription": {"text": "Speech text here"},
        }
        a._call_mcp_tool = AsyncMock(return_value={"status": "success", "result": tool_response})
        result = await a.process_youtube_video("https://youtube.com/watch?v=transcription")
        assert result["status"] == "completed"

    async def test_processing_with_structured_tasks(self, tmp_path):
        """Covers the 'structured_tasks' extension branch"""
        a = make_subagent(tmp_path)
        tool_response = {
            "status": "completed",
            "structured_tasks": [{"type": "task", "description": "Some task"}],
        }
        a._call_mcp_tool = AsyncMock(return_value={"status": "success", "result": tool_response})
        result = await a.process_youtube_video("https://youtube.com/watch?v=tasks")
        assert result["status"] == "completed"
        assert len(result["generated_actions"]) >= 1
