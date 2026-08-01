"""Unit tests for SkillBuilder, _skill_id, _now_iso helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

# Stub the broken services __init__ before importing submodules
import types as _types  # noqa: E402

if "youtube_extension.services" not in sys.modules:
    _stub = _types.ModuleType("youtube_extension.services")
    _stub.__path__ = [str(_SRC / "youtube_extension/services")]
    _stub.__package__ = "youtube_extension.services"
    sys.modules["youtube_extension.services"] = _stub

# Force reimport so pytest-cov can instrument the module even if it was
# previously cached in sys.modules from a broken import attempt.
sys.modules.pop("youtube_extension.services.skill_builder", None)

from youtube_extension.services.skill_builder import (  # noqa: E402
    SkillBuilder,
    _now_iso,
    _skill_id,
    get_skill_builder,
)

# ===========================================================================
# Module-level helpers
# ===========================================================================


class TestSkillId:
    def test_returns_string(self):
        result = _skill_id("nextjs", "vercel")
        assert isinstance(result, str)

    def test_length_16(self):
        assert len(_skill_id("nextjs", "vercel")) == 16

    def test_same_input_same_output(self):
        assert _skill_id("nextjs", "vercel") == _skill_id("nextjs", "vercel")

    def test_different_inputs_different_output(self):
        assert _skill_id("nextjs", "vercel") != _skill_id("react", "netlify")

    def test_case_insensitive(self):
        assert _skill_id("NextJS", "Vercel") == _skill_id("nextjs", "vercel")


class TestNowIso:
    def test_returns_string(self):
        result = _now_iso()
        assert isinstance(result, str)

    def test_contains_timezone_marker(self):
        # ISO 8601 with UTC should have +00:00 or Z
        result = _now_iso()
        assert "+" in result or "Z" in result


# ===========================================================================
# SkillBuilder.__init__
# ===========================================================================


class TestSkillBuilderInit:
    def test_creates_skills_dir(self, tmp_path):
        skills_dir = tmp_path / "skills"
        sb = SkillBuilder(skills_dir=skills_dir)
        assert skills_dir.exists()

    def test_skills_dir_stored(self, tmp_path):
        skills_dir = tmp_path / "skills"
        sb = SkillBuilder(skills_dir=skills_dir)
        assert sb.skills_dir == skills_dir


# ===========================================================================
# SkillBuilder.record_deployment
# ===========================================================================


class TestSkillBuilderRecordDeployment:
    def test_creates_skill_file(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        skill_files = list(tmp_path.glob("*.skill.json"))
        assert len(skill_files) == 1

    def test_skill_file_has_events(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert len(data["events"]) == 1

    def test_success_updates_success_rate_up(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        # Starting at 0.5, one success should push above 0.5
        assert data["success_rate"] > 0.5

    def test_failure_updates_success_rate_down(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=False)
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert data["success_rate"] < 0.5

    def test_multiple_events_accumulate(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        sb.record_deployment("nextjs", "vercel", success=True)
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert len(data["events"]) == 2

    def test_event_has_framework_field(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert data["events"][0]["framework"] == "nextjs"

    def test_event_has_error_message(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=False, error_message="Build failed!")
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert data["events"][0]["error_message"] == "Build failed!"

    def test_different_frameworks_create_separate_files(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        sb.record_deployment("fastapi", "fly", success=True)
        skill_files = list(tmp_path.glob("*.skill.json"))
        assert len(skill_files) == 2

    def test_node_version_error_creates_lesson(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment(
            "nextjs", "vercel", success=False,
            error_message="Node version mismatch detected",
            config={"node_version": "18"}
        )
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert len(data["lessons"]) > 0

    def test_success_with_config_creates_lesson(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment(
            "nextjs", "vercel", success=True,
            config={"node_version": "20", "build_cmd": "npm run build"}
        )
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert len(data["lessons"]) > 0


# ===========================================================================
# SkillBuilder.get_context
# ===========================================================================


class TestSkillBuilderGetContext:
    def test_returns_dict(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        ctx = sb.get_context("nextjs", "vercel")
        assert isinstance(ctx, dict)

    def test_has_lessons_key(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        ctx = sb.get_context("nextjs", "vercel")
        assert "lessons" in ctx

    def test_has_framework_key(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        ctx = sb.get_context("nextjs", "vercel")
        assert ctx["framework"] == "nextjs"

    def test_has_deployment_target_key(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        ctx = sb.get_context("nextjs", "vercel")
        assert ctx["deployment_target"] == "vercel"

    def test_no_data_initially(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        ctx = sb.get_context("nextjs", "vercel")
        assert ctx["has_data"] is False

    def test_has_data_after_recording(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        ctx = sb.get_context("nextjs", "vercel")
        assert ctx["has_data"] is True

    def test_lessons_list_from_records(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment(
            "nextjs", "vercel", success=False,
            error_message="Build command failed and was not found"
        )
        ctx = sb.get_context("nextjs", "vercel")
        assert isinstance(ctx["lessons"], list)


# ===========================================================================
# SkillBuilder.list_skills
# ===========================================================================


class TestSkillBuilderListSkills:
    def test_empty_initially(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        assert sb.list_skills() == []

    def test_lists_after_recording(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        skills = sb.list_skills()
        assert len(skills) == 1

    def test_summary_has_framework(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        summary = sb.list_skills()[0]
        assert summary["framework"] == "nextjs"

    def test_summary_has_deployment_target(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        summary = sb.list_skills()[0]
        assert summary["deployment_target"] == "vercel"

    def test_multiple_skills_listed(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        sb.record_deployment("fastapi", "fly", success=False)
        skills = sb.list_skills()
        assert len(skills) == 2


# ===========================================================================
# SkillBuilder.reset_skill
# ===========================================================================


class TestSkillBuilderResetSkill:
    def test_reset_removes_skill_file(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        sb.reset_skill("nextjs", "vercel")
        assert list(tmp_path.glob("*.skill.json")) == []

    def test_reset_nonexistent_does_not_raise(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.reset_skill("nextjs", "vercel")  # should not raise

    def test_after_reset_no_data(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        sb.record_deployment("nextjs", "vercel", success=True)
        sb.reset_skill("nextjs", "vercel")
        ctx = sb.get_context("nextjs", "vercel")
        assert ctx["has_data"] is False


# ===========================================================================
# _lesson_from_error static method
# ===========================================================================


class TestLessonFromError:
    def test_node_version_error(self):
        lesson = SkillBuilder._lesson_from_error(
            "nextjs", "vercel", "Node version mismatch engine error", {"node_version": "18"}
        )
        assert "NODE_VERSION=18" in lesson

    def test_python_version_error(self):
        lesson = SkillBuilder._lesson_from_error(
            "fastapi", "fly", "Python version incompatible", {"python_version": "3.11"}
        )
        assert "python-3.11" in lesson

    def test_build_failure_error(self):
        lesson = SkillBuilder._lesson_from_error(
            "nextjs", "vercel", "Build command failed", {}
        )
        assert "Build failure" in lesson

    def test_env_variable_error(self):
        lesson = SkillBuilder._lesson_from_error(
            "nextjs", "vercel", "Missing environment variable: DATABASE_URL", {}
        )
        assert "DATABASE_URL" in lesson

    def test_generic_error_fallback(self):
        lesson = SkillBuilder._lesson_from_error(
            "nextjs", "vercel", "Something weird happened", {}
        )
        assert "nextjs" in lesson
        assert "vercel" in lesson


# ===========================================================================
# _lesson_from_success static method
# ===========================================================================


class TestLessonFromSuccess:
    def test_returns_none_for_empty_config(self):
        assert SkillBuilder._lesson_from_success("nextjs", "vercel", {}) is None

    def test_returns_lesson_with_config(self):
        lesson = SkillBuilder._lesson_from_success(
            "nextjs", "vercel", {"node_version": "20"}
        )
        assert lesson is not None
        assert "nextjs" in lesson

    def test_returns_none_for_all_falsy_config(self):
        assert SkillBuilder._lesson_from_success("nextjs", "vercel", {"key": None}) is None


# ===========================================================================
# get_skill_builder singleton
# ===========================================================================


class TestGetSkillBuilder:
    def test_returns_skill_builder_instance(self, tmp_path):
        sb = get_skill_builder(skills_dir=tmp_path)
        assert isinstance(sb, SkillBuilder)


# ===========================================================================
# _add_lesson: deduplication and pruning
# ===========================================================================


class TestAddLesson:
    def test_same_lesson_increments_count(self, tmp_path):
        sb = SkillBuilder(skills_dir=tmp_path)
        # Two identical errors generate the same lesson → dedup
        cfg = {"node_version": "18"}
        sb.record_deployment("nextjs", "vercel", success=False,
                             error_message="Node version mismatch engine", config=cfg)
        sb.record_deployment("nextjs", "vercel", success=False,
                             error_message="Node version mismatch engine", config=cfg)
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        # Same lesson key means count should be 2
        lesson_counts = [v["count"] for v in data["lessons"].values()]
        assert any(c >= 2 for c in lesson_counts)

    def test_pruning_keeps_max_lessons(self, tmp_path):
        from youtube_extension.services.skill_builder import _MAX_LESSONS_PER_SKILL
        sb = SkillBuilder(skills_dir=tmp_path)
        # Generate > _MAX_LESSONS_PER_SKILL unique lessons
        for i in range(_MAX_LESSONS_PER_SKILL + 5):
            sb.record_deployment(
                "nextjs", "vercel", success=False,
                error_message=f"Unique error number {i:04d} occurred"
            )
        skill_file = list(tmp_path.glob("*.skill.json"))[0]
        data = json.loads(skill_file.read_text())
        assert len(data["lessons"]) <= _MAX_LESSONS_PER_SKILL


class TestListSkillsCorruptFile:
    """list_skills silently ignores corrupt skill files (lines 208-209)"""

    def test_corrupt_json_is_skipped(self, tmp_path):
        from youtube_extension.services.skill_builder import (
            _SKILL_FILE_SUFFIX,
            SkillBuilder,
        )
        sb = SkillBuilder(skills_dir=tmp_path)
        # Write one valid skill
        sb.record_deployment("react", "netlify", success=True)
        # Write a corrupt file that matches the glob pattern
        corrupt = tmp_path / f"corrupt_skill{_SKILL_FILE_SUFFIX}"
        corrupt.write_text("{invalid json}")
        # list_skills should still return the valid entry without raising
        summaries = sb.list_skills()
        assert isinstance(summaries, list)
        # Should contain the valid react/netlify entry
        assert any(s.get("framework") == "react" for s in summaries)


class TestLoadSkillCorruptFile:
    """_load_skill silently returns default for corrupt file (lines 229-230)"""

    def test_corrupt_json_returns_default(self, tmp_path):
        from youtube_extension.services.skill_builder import (
            _SKILL_FILE_SUFFIX,
            SkillBuilder,
            _skill_id,
        )
        sb = SkillBuilder(skills_dir=tmp_path)
        sid = _skill_id("django", "fly")
        # Write a corrupt skill file directly
        skill_path = tmp_path / f"{sid}{_SKILL_FILE_SUFFIX}"
        skill_path.write_text("{not valid json")
        # _load_skill should return the default structure
        result = sb._load_skill(sid)
        assert result == {"events": [], "lessons": {}, "success_rate": 0.5}
