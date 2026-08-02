"""Tests for the lightweight project code generator."""

from __future__ import annotations

import asyncio
import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from youtube_extension.backend.code_generator import (
    ProjectCodeGenerator,
    _apply_write_plan,
    _build_title,
    _extract_video_id,
    _run_offloop,
    get_code_generator,
)


def _tempdir_factory(*paths: Path):
    remaining = iter(paths)

    def _mkdtemp(prefix: str) -> str:
        path = next(remaining)
        path.mkdir()
        return str(path)

    return _mkdtemp


def _build_video_analysis(title: str, video_id: str, summary: str, concepts: list[str]) -> dict:
    return {
        "metadata": {"title": title, "video_id": video_id},
        "video_data": {
            "video_id": video_id,
            "video_url": f"https://youtu.be/{video_id}",
        },
        "ai_analysis": {
            "Content Summary": summary,
            "Key Concepts": concepts,
            "Related Topics": ["javascript", "html", "css"],
        },
        "build_plan": {
            "video_id": video_id,
            "video_title": title,
            "project_type": "web",
            "technologies": ["javascript", "html", "css"],
            "summary": summary,
            "steps": [
                {
                    "order": 1,
                    "action": "create_file",
                    "target_file": "index.html",
                    "description": "Create the main page shell",
                },
                {
                    "order": 2,
                    "action": "create_file",
                    "target_file": "main.js",
                    "description": "Wire up the interactive tutorial behavior",
                },
            ],
        },
        "success": True,
    }


def test_generate_project_includes_video_specific_content(monkeypatch, tmp_path) -> None:
    """Ensure generated assets reflect the source video instead of boilerplate."""

    project_dir = tmp_path / "uvai_generated_project"
    project_dir.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

    generator = ProjectCodeGenerator(use_ai_generation=False)
    video_analysis = {
        "metadata": {"title": "Build a React Weather App", "keywords": ["react", "api"]},
        "ai_analysis": {
            "Content Summary": "Walks through building a weather dashboard with React hooks.",
            "Related Topics": ["react", "hooks", "api integration"],
            "Key Concepts": ["state management", "effects", "api calls"],
            "Learning Path": "Set up React\nFetch weather data\nRender dashboard",
        },
        "transcript": {"text": "Set up React. Fetch weather data. Render dashboard components."},
        "success": True,
    }
    project_config = {"type": "web", "features": ["api_integration"]}

    result = asyncio.run(generator.generate_project(video_analysis, project_config))
    generated_path = Path(result["project_path"])

    readme_text = (generated_path / "README.md").read_text()
    assert "Build a React Weather App" in readme_text
    assert "Video Summary" in readme_text
    assert "weather dashboard with React hooks" in readme_text
    assert "Key Concepts From The Tutorial" in readme_text

    app_text = (generated_path / "src" / "App.js").read_text()
    assert "React Weather App" in app_text
    assert "state management" in app_text or "api calls" in app_text


def test_build_plan_videos_generate_unique_vanilla_assets(monkeypatch, tmp_path) -> None:
    """Ensure BuildPlan-backed vanilla generation stays tutorial-specific."""

    project_one = tmp_path / "project_one"
    project_two = tmp_path / "project_two"
    monkeypatch.setattr(tempfile, "mkdtemp", _tempdir_factory(project_one, project_two))

    generator = ProjectCodeGenerator(use_ai_generation=False)
    project_config = {"type": "web", "features": ["responsive_design"]}

    first = asyncio.run(
        generator.generate_project(
            _build_video_analysis(
                "Build a Todo App",
                "todo123",
                "Creates a todo list with local storage.",
                ["local storage", "dom events"],
            ),
            project_config,
        )
    )
    second = asyncio.run(
        generator.generate_project(
            _build_video_analysis(
                "Build a Weather Dashboard",
                "weather456",
                "Builds a weather dashboard with API-driven cards.",
                ["fetch api", "forecast cards"],
            ),
            project_config,
        )
    )

    first_path = Path(first["project_path"])
    second_path = Path(second["project_path"])

    assert (first_path / "main.js").read_text() != (second_path / "main.js").read_text()
    assert (first_path / "styles.css").read_text() != (second_path / "styles.css").read_text()
    assert first["build_plan"]["steps"][0]["order"] == 1

    for file_name in ("index.html", "main.js", "styles.css", "README.md"):
        assert "Build a Todo App" in (first_path / file_name).read_text()
        assert "Build a Weather Dashboard" in (second_path / file_name).read_text()


def test_same_build_plan_video_produces_deterministic_vanilla_files(monkeypatch, tmp_path) -> None:
    """Ensure repeated generation for the same tutorial is deterministic."""

    first_project = tmp_path / "deterministic_one"
    second_project = tmp_path / "deterministic_two"
    monkeypatch.setattr(
        tempfile,
        "mkdtemp",
        _tempdir_factory(first_project, second_project),
    )

    generator = ProjectCodeGenerator(use_ai_generation=False)
    video_analysis = _build_video_analysis(
        "Build a Recipe Finder",
        "recipe789",
        "Builds a recipe finder with searchable ingredient cards.",
        ["search filtering", "ingredient cards"],
    )
    project_config = {"type": "web", "features": ["responsive_design"]}

    first = asyncio.run(generator.generate_project(video_analysis, project_config))
    second = asyncio.run(generator.generate_project(video_analysis, project_config))

    first_path = Path(first["project_path"])
    second_path = Path(second["project_path"])

    for file_name in ("index.html", "main.js", "styles.css", "README.md"):
        assert (first_path / file_name).read_text() == (second_path / file_name).read_text()


# ===========================================================================
# _extract_video_id
# ===========================================================================


class TestExtractVideoId:
    def test_standard_youtube_url(self):
        assert _extract_video_id("https://www.youtube.com/watch?v=auJzb1D-fag") == "auJzb1D-fag"

    def test_youtube_com_without_www(self):
        assert _extract_video_id("https://youtube.com/watch?v=abc12345678") == "abc12345678"

    def test_youtu_be_short_url(self):
        assert _extract_video_id("https://youtu.be/auJzb1D-fag") == "auJzb1D-fag"

    def test_youtu_be_with_trailing_slash(self):
        assert _extract_video_id("https://youtu.be/") is None

    def test_returns_none_for_non_youtube_url(self):
        assert _extract_video_id("https://vimeo.com/12345") is None

    def test_returns_none_for_empty_string(self):
        assert _extract_video_id("") is None

    def test_returns_none_for_none_input(self):
        assert _extract_video_id(None) is None

    def test_url_with_extra_query_params(self):
        vid_id = _extract_video_id("https://www.youtube.com/watch?v=abc12345678&t=30s")
        assert vid_id == "abc12345678"


# ===========================================================================
# _build_title
# ===========================================================================


class TestBuildTitle:
    def test_uses_extracted_info_title_first(self):
        title = _build_title({"title": "Extracted Title"}, {"metadata": {"title": "Meta Title"}}, "Default")
        assert title == "Extracted Title"

    def test_falls_back_to_metadata_title(self):
        title = _build_title({}, {"metadata": {"title": "Meta Title"}}, "Default")
        assert title == "Meta Title"

    def test_falls_back_to_video_id_label(self):
        video_analysis = {
            "video_data": {"video_url": "https://youtu.be/abc12345678"},
        }
        title = _build_title({}, video_analysis, "Default")
        assert "abc12345678" in title

    def test_uses_default_when_no_info(self):
        title = _build_title({}, {}, "My Default")
        assert title == "My Default"

    def test_video_url_from_metadata_key(self):
        video_analysis = {"metadata": {"video_url": "https://youtu.be/xyz98765432"}}
        title = _build_title({}, video_analysis, "Default")
        assert "xyz98765432" in title

    def test_video_url_from_video_url_key(self):
        video_analysis = {"video_url": "https://youtu.be/vid11111111"}
        title = _build_title({}, video_analysis, "Default")
        assert "vid11111111" in title


# ===========================================================================
# ProjectCodeGenerator helpers
# ===========================================================================


class TestProjectCodeGeneratorHelpers:
    @pytest.fixture
    def gen(self):
        return ProjectCodeGenerator(use_ai_generation=False)

    def test_sanitize_name_removes_special_chars(self, gen):
        assert gen._sanitize_name("Hello World!") == "hello-world"

    def test_sanitize_name_converts_spaces_to_dashes(self, gen):
        assert gen._sanitize_name("My React App") == "my-react-app"

    def test_sanitize_name_truncates_long_names(self, gen):
        long_name = "a" * 100
        assert len(gen._sanitize_name(long_name)) <= 50

    def test_sanitize_name_empty_returns_default(self, gen):
        assert gen._sanitize_name("") == "uvai-project"

    def test_sanitize_name_starts_with_digit_gets_prefix(self, gen):
        result = gen._sanitize_name("123project")
        assert result.startswith("uvai-") or result[0].isalpha()

    def test_video_fingerprint_is_deterministic(self, gen):
        fp1 = gen._video_fingerprint("vid1", "Title", ["js", "html"])
        fp2 = gen._video_fingerprint("vid1", "Title", ["js", "html"])
        assert fp1 == fp2

    def test_video_fingerprint_length_12(self, gen):
        fp = gen._video_fingerprint("vid1", "Title", ["js"])
        assert len(fp) == 12

    def test_video_fingerprint_changes_with_different_inputs(self, gen):
        fp1 = gen._video_fingerprint("vid1", "Title A", ["js"])
        fp2 = gen._video_fingerprint("vid2", "Title B", ["python"])
        assert fp1 != fp2

    def test_accent_from_fingerprint_returns_hsl(self, gen):
        fp = gen._video_fingerprint("vid", "title", ["js"])
        color = gen._accent_from_fingerprint(fp)
        assert color.startswith("hsl(")

    def test_accent_dark_from_fingerprint_returns_hsl(self, gen):
        fp = gen._video_fingerprint("vid", "title", ["js"])
        color = gen._accent_dark_from_fingerprint(fp)
        assert color.startswith("hsl(")

    def test_coerce_to_list_from_list(self, gen):
        assert gen._coerce_to_list(["a", "b"]) == ["a", "b"]

    def test_coerce_to_list_from_comma_string(self, gen):
        result = gen._coerce_to_list("react, vue, angular")
        assert "react" in result
        assert "vue" in result

    def test_coerce_to_list_from_pipe_string(self, gen):
        result = gen._coerce_to_list("react|vue|angular")
        assert len(result) == 3

    def test_coerce_to_list_returns_empty_for_none(self, gen):
        assert gen._coerce_to_list(None) == []

    def test_coerce_to_list_returns_empty_for_empty_string(self, gen):
        assert gen._coerce_to_list("") == []

    def test_coerce_to_list_single_item_string(self, gen):
        assert gen._coerce_to_list("javascript") == ["javascript"]

    def test_build_plan_steps_to_list_empty_plan(self, gen):
        assert gen._build_plan_steps_to_list(None) == []

    def test_build_plan_steps_to_list_empty_steps(self, gen):
        assert gen._build_plan_steps_to_list({"steps": []}) == []

    def test_build_plan_steps_to_list_with_steps(self, gen):
        plan = {
            "steps": [
                {"order": 1, "action": "create_file", "target_file": "index.html", "description": "Create HTML shell"},
            ]
        }
        result = gen._build_plan_steps_to_list(plan)
        assert len(result) == 1
        assert "create_file" in result[0]
        assert "index.html" in result[0]

    def test_build_plan_steps_to_list_missing_fields(self, gen):
        plan = {"steps": [{"action": "do_thing"}]}
        result = gen._build_plan_steps_to_list(plan)
        assert len(result) == 1
        assert "do_thing" in result[0]


# ===========================================================================
# _derive_tutorial_steps
# ===========================================================================


class TestDeriveTutorialSteps:
    @pytest.fixture
    def gen(self):
        return ProjectCodeGenerator(use_ai_generation=False)

    def test_from_learning_path_in_ai_analysis(self, gen):
        ai_analysis = {"Learning Path": "Step one\nStep two\nStep three"}
        steps = gen._derive_tutorial_steps(ai_analysis, {})
        assert len(steps) >= 2
        assert "Step one" in steps

    def test_from_transcript_when_no_learning_path(self, gen):
        video_analysis = {"transcript": {"text": "First sentence. Second sentence. Third sentence."}}
        steps = gen._derive_tutorial_steps({}, video_analysis)
        assert len(steps) >= 1

    def test_from_markdown_when_no_transcript(self, gen):
        video_analysis = {"markdown_analysis": "- install deps\n* run build\n- deploy"}
        steps = gen._derive_tutorial_steps({}, video_analysis)
        assert len(steps) >= 1

    def test_returns_empty_list_when_no_sources(self, gen):
        steps = gen._derive_tutorial_steps({}, {})
        assert steps == []

    def test_max_eight_steps_returned(self, gen):
        ai_analysis = {"Learning Path": "\n".join([f"Step {i}" for i in range(20)])}
        steps = gen._derive_tutorial_steps(ai_analysis, {})
        assert len(steps) <= 8


# ===========================================================================
# _extract_summary
# ===========================================================================


class TestExtractSummary:
    @pytest.fixture
    def gen(self):
        return ProjectCodeGenerator(use_ai_generation=False)

    def test_from_ai_analysis(self, gen):
        ai_analysis = {"Content Summary": "This tutorial explains how to build a todo app."}
        summary = gen._extract_summary(ai_analysis, {})
        assert "todo app" in summary

    def test_from_markdown_when_no_ai_summary(self, gen):
        video_analysis = {"markdown_analysis": "Line 1\nLine 2\nLine 3"}
        summary = gen._extract_summary({}, video_analysis)
        assert len(summary) > 0

    def test_from_transcript_when_no_markdown(self, gen):
        video_analysis = {"transcript": {"text": "Welcome to this tutorial on React hooks."}}
        summary = gen._extract_summary({}, video_analysis)
        assert "React hooks" in summary

    def test_returns_empty_when_no_sources(self, gen):
        summary = gen._extract_summary({}, {})
        assert summary == ""

    def test_truncates_at_600_chars(self, gen):
        long_line = "word " * 200
        video_analysis = {"markdown_analysis": long_line}
        summary = gen._extract_summary({}, video_analysis)
        assert len(summary) <= 600


# ===========================================================================
# generate_project — API project type
# ===========================================================================


class TestGenerateApiProject:
    def test_python_api_project_creates_main_py(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "api_project"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Build a FastAPI App",
                "technologies": ["python"],
                "features": [],
                "project_type": "api",
            },
            "success": True,
        }
        result = asyncio.run(gen.generate_project(video_analysis, {"type": "api"}))
        assert (project_dir / "main.py").exists()
        assert result["framework"] == "fastapi"

    def test_python_api_with_auth_feature_adds_auth_route(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "api_auth"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Auth API",
                "technologies": ["python"],
                "features": ["authentication"],
                "project_type": "api",
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "api"}))
        main_py = (project_dir / "main.py").read_text()
        assert "auth/login" in main_py or "JWT" in main_py or "SECRET_KEY" in main_py

    def test_python_api_with_database_feature(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "api_db"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "DB API",
                "technologies": ["python"],
                "features": ["database"],
                "project_type": "api",
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "api"}))
        main_py = (project_dir / "main.py").read_text()
        assert "database" in main_py.lower() or "sqlalchemy" in main_py.lower() or "data" in main_py.lower()

    def test_api_requirements_txt_created(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "api_reqs"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "FastAPI Project",
                "technologies": ["python"],
                "features": [],
                "project_type": "api",
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "api"}))
        reqs = (project_dir / "requirements.txt").read_text()
        assert "fastapi" in reqs


# ===========================================================================
# generate_project — React project type
# ===========================================================================


class TestGenerateReactProject:
    def test_react_project_creates_src_files(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "react_project"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "My React App",
                "technologies": ["react"],
                "features": [],
                "project_type": "web",
            },
            "success": True,
        }
        result = asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        assert result["framework"] == "react"
        assert (project_dir / "src" / "App.js").exists()
        assert (project_dir / "src" / "index.js").exists()
        assert (project_dir / "package.json").exists()

    def test_react_project_package_json_has_react_dep(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "react_pkg"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "React App",
                "technologies": ["react"],
                "features": [],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        pkg = json.loads((project_dir / "package.json").read_text())
        assert "react" in pkg["dependencies"]

    def test_react_project_with_auth_adds_auth0(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "react_auth"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Auth App",
                "technologies": ["react"],
                "features": ["authentication"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        pkg = json.loads((project_dir / "package.json").read_text())
        assert "@auth0/auth0-react" in pkg["dependencies"]

    def test_react_project_with_responsive_adds_tailwind(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "react_tailwind"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Tailwind App",
                "technologies": ["react"],
                "features": ["responsive_design"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        pkg = json.loads((project_dir / "package.json").read_text())
        assert "tailwindcss" in pkg["dependencies"]

    def test_react_app_css_with_responsive_has_media_query(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "react_resp"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Responsive App",
                "technologies": ["react"],
                "features": ["responsive_design"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        css = (project_dir / "src" / "App.css").read_text()
        assert "@media" in css


# ===========================================================================
# generate_project — vanilla JS with features
# ===========================================================================


class TestGenerateVanillaProject:
    def test_vanilla_main_js_has_api_fetch_when_api_integration(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "vanilla_api"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "API App",
                "technologies": ["javascript"],
                "features": ["api_integration"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        main_js = (project_dir / "main.js").read_text()
        assert "fetchData" in main_js or "fetch" in main_js

    def test_vanilla_main_js_has_auth_when_authentication(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "vanilla_auth"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Auth App",
                "technologies": ["javascript"],
                "features": ["authentication"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        main_js = (project_dir / "main.js").read_text()
        assert "initAuth" in main_js or "auth" in main_js.lower()

    def test_vanilla_main_js_has_database_when_database_feature(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "vanilla_db"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "DB App",
                "technologies": ["javascript"],
                "features": ["database"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        main_js = (project_dir / "main.js").read_text()
        assert "initDatabase" in main_js or "database" in main_js.lower()

    def test_vanilla_styles_responsive_has_media_query(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "vanilla_resp"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Responsive Vanilla",
                "technologies": ["javascript"],
                "features": ["responsive_design"],
            },
            "success": True,
        }
        asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        css = (project_dir / "styles.css").read_text()
        assert "@media" in css

    def test_vue_project_falls_back_to_vanilla(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "vue_proj"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Vue App",
                "technologies": ["vue"],
                "features": [],
            },
            "success": True,
        }
        result = asyncio.run(gen.generate_project(video_analysis, {"type": "web"}))
        # Vue is not fully implemented, falls back to vanilla
        assert result["framework"] == "vanilla"

    def test_mobile_project_falls_back_to_web(self, monkeypatch, tmp_path):
        project_dir = tmp_path / "mobile_proj"
        project_dir.mkdir()
        monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

        gen = ProjectCodeGenerator(use_ai_generation=False)
        video_analysis = {
            "extracted_info": {
                "title": "Mobile App",
                "technologies": ["javascript"],
                "features": [],
            },
            "success": True,
        }
        result = asyncio.run(gen.generate_project(video_analysis, {"type": "mobile"}))
        # Mobile falls back to web (vanilla)
        assert "framework" in result


# ===========================================================================
# _build_generation_context
# ===========================================================================


class TestBuildGenerationContext:
    @pytest.fixture
    def gen(self):
        return ProjectCodeGenerator(use_ai_generation=False)

    def test_uses_build_plan_when_present(self, gen):
        video_analysis = {
            "metadata": {"title": "Tutorial Title"},
            "build_plan": {
                "video_title": "Tutorial Title",
                "project_type": "web",
                "technologies": ["react"],
                "features": ["authentication"],
                "summary": "Build a full-stack app",
                "steps": [{"order": 1, "action": "create_file", "target_file": "index.html", "description": "shell"}],
            }
        }
        ctx = gen._build_generation_context(video_analysis, {})
        assert ctx["extracted_info"]["title"] == "Tutorial Title"
        assert ctx["build_plan"] is not None

    def test_falls_back_to_legacy_without_build_plan(self, gen):
        video_analysis = {
            "extracted_info": {
                "title": "Legacy Title",
                "technologies": ["javascript"],
                "features": ["responsive_design"],
            }
        }
        ctx = gen._build_generation_context(video_analysis, {})
        assert ctx["extracted_info"]["title"] == "Legacy Title"

    def test_default_technologies_when_none_provided(self, gen):
        ctx = gen._build_generation_context({}, {})
        assert "javascript" in ctx["extracted_info"]["technologies"]

    def test_project_config_type_overrides_extracted_type(self, gen):
        video_analysis = {"extracted_info": {"project_type": "web"}}
        ctx = gen._build_generation_context(video_analysis, {"type": "api"})
        assert ctx["extracted_info"]["project_type"] == "api"

    def test_pydantic_build_plan_is_dumped(self, gen):
        class FakePlan:
            def model_dump(self):
                return {"video_title": "Pydantic Plan", "project_type": "web", "technologies": [], "steps": []}

        video_analysis = {"build_plan": FakePlan()}
        ctx = gen._build_generation_context(video_analysis, {})
        assert isinstance(ctx["build_plan"], dict)

    def test_tutorial_steps_from_build_plan_steps(self, gen):
        video_analysis = {
            "build_plan": {
                "video_title": "Title",
                "project_type": "web",
                "technologies": ["js"],
                "steps": [
                    {"order": 1, "description": "first step"},
                    {"order": 2, "description": "second step"},
                ],
            }
        }
        ctx = gen._build_generation_context(video_analysis, {})
        steps = ctx["extracted_info"]["tutorial_steps"]
        assert len(steps) >= 2
        assert "first step" in steps[0]


# ===========================================================================
# get_code_generator (module-level singleton)
# ===========================================================================


class TestGetCodeGenerator:
    def test_returns_project_code_generator_instance(self):
        gen = get_code_generator(use_ai_generation=False)
        assert isinstance(gen, ProjectCodeGenerator)

    def test_returns_same_instance_on_repeated_calls(self):
        # Reset global for isolation
        import youtube_extension.backend.code_generator as cg_module
        cg_module._code_generator = None
        gen1 = get_code_generator(use_ai_generation=False)
        gen2 = get_code_generator(use_ai_generation=False)
        assert gen1 is gen2
        cg_module._code_generator = None  # clean up


# ===========================================================================
# Scaffolding disk I/O runs off the event loop (issue #1250)
# ===========================================================================


class TestScaffoldingWritesOffLoop:
    """Every filesystem call must land on a worker thread, not the loop.

    These assert *thread identity* rather than elapsed time: a wall-clock
    threshold would be flaky under CI contention and would still pass if the
    work ran on the loop but happened to be fast.
    """

    @staticmethod
    def _recording_open(record: list[str]):
        """Wrap ``builtins.open`` so each call records its executing thread."""
        import builtins

        real_open = builtins.open

        def _tracked(*args, **kwargs):
            record.append(threading.current_thread().name)
            return real_open(*args, **kwargs)

        return _tracked

    @pytest.mark.parametrize(
        "generator_name",
        [
            "_generate_react_project",
            "_generate_vanilla_js_project",
            "_generate_python_api",
        ],
    )
    async def test_generator_writes_never_touch_loop_thread(
        self, monkeypatch, tmp_path, generator_name
    ):
        gen = ProjectCodeGenerator(use_ai_generation=False)
        analysis = _build_video_analysis(
            "Dashboard Tutorial", "auJzb1D-fag", "A summary.", ["state", "charts"]
        )
        loop_thread = threading.current_thread().name

        seen: list[str] = []
        monkeypatch.setattr("builtins.open", self._recording_open(seen))

        project = tmp_path / "project"
        project.mkdir()
        await getattr(gen, generator_name)(project, analysis, ["database"])

        assert seen, "expected the generator to write at least one file"
        offenders = [name for name in seen if name == loop_thread]
        assert not offenders, (
            f"{generator_name} performed {len(offenders)} of {len(seen)} writes "
            f"on the event loop thread ({loop_thread})"
        )

    async def test_mkdtemp_runs_off_loop(self, monkeypatch, tmp_path):
        """The project directory itself is also created off-loop."""
        import youtube_extension.backend.code_generator as cg_module

        loop_thread = threading.current_thread().name
        seen: list[str] = []
        real_mkdtemp = tempfile.mkdtemp

        def _tracked(*args, **kwargs):
            seen.append(threading.current_thread().name)
            return real_mkdtemp(*args, **kwargs)

        monkeypatch.setattr(cg_module.tempfile, "mkdtemp", _tracked)

        gen = ProjectCodeGenerator(use_ai_generation=False)
        await gen.generate_project(
            _build_video_analysis("T", "auJzb1D-fag", "S", []),
            {"project_type": "web", "technologies": ["react"]},
        )

        assert seen, "expected mkdtemp to be called"
        assert loop_thread not in seen, (
            f"tempfile.mkdtemp ran on the event loop thread ({loop_thread})"
        )

    @pytest.mark.parametrize(
        ("generator_name", "expected_files"),
        [
            ("_generate_react_project", 6),
            ("_generate_vanilla_js_project", 4),
            ("_generate_python_api", 3),
        ],
    )
    async def test_batches_into_a_single_thread_hop(
        self, monkeypatch, tmp_path, generator_name, expected_files
    ):
        """Cost is O(1) thread hops per generator, not O(files).

        Guards against a regression that offloads each write individually,
        which would still pass the thread-identity tests above while paying
        one context switch per file.
        """
        import youtube_extension.backend.code_generator as cg_module

        real_to_thread = asyncio.to_thread
        hops: list[str] = []

        async def _counting(func, /, *args, **kwargs):
            hops.append(getattr(func, "__name__", repr(func)))
            return await real_to_thread(func, *args, **kwargs)

        monkeypatch.setattr(cg_module.asyncio, "to_thread", _counting)

        gen = ProjectCodeGenerator(use_ai_generation=False)
        project = tmp_path / "project"
        project.mkdir()
        await getattr(gen, generator_name)(
            project,
            _build_video_analysis("T", "auJzb1D-fag", "S", []),
            ["database"],
        )

        assert hops == ["_apply_write_plan"], (
            f"expected exactly one batched hop, got {hops}"
        )
        written = [p for p in project.rglob("*") if p.is_file()]
        assert len(written) == expected_files


class TestApplyWritePlan:
    """Contract of the batched write helper itself."""

    def test_applies_steps_in_order_so_dirs_precede_their_files(self, tmp_path):
        nested = tmp_path / "src"
        plan = [
            (nested, None),
            (nested / "App.js", "console.log(1);"),
        ]
        _apply_write_plan(plan)

        assert nested.is_dir()
        assert (nested / "App.js").read_text() == "console.log(1);"

    def test_directory_step_tolerates_an_existing_directory(self, tmp_path):
        existing = tmp_path / "public"
        existing.mkdir()
        _apply_write_plan([(existing, None)])  # must not raise
        assert existing.is_dir()

    def test_does_not_suppress_errors_and_leaves_earlier_steps_applied(
        self, tmp_path
    ):
        """A failing step raises, exactly as the inline sequence did.

        Uses a real invalid path rather than a mock so the stdlib itself
        produces the failure.
        """
        good = tmp_path / "first.txt"
        plan = [
            (good, "written"),
            (tmp_path / "bad\x00name.txt", "never"),
            (tmp_path / "third.txt", "unreached"),
        ]

        with pytest.raises(ValueError, match="null"):
            _apply_write_plan(plan)

        assert good.read_text() == "written"
        assert not (tmp_path / "third.txt").exists()

    def test_writes_content_verbatim_without_adding_a_trailing_newline(
        self, tmp_path
    ):
        target = tmp_path / "package.json"
        payload = json.dumps({"name": "x", "version": "1.0.0"}, indent=2)
        _apply_write_plan([(target, payload)])
        assert target.read_bytes() == payload.encode()


class TestRunOffloop:
    """``_run_offloop`` must not abandon a worker thread on cancellation.

    ``asyncio.to_thread`` cannot interrupt a thread that has already started, so
    the helper shields the worker and waits for it to settle before propagating
    the cancellation — otherwise a caller's cleanup would race a live writer.
    """

    async def test_returns_worker_result_on_happy_path(self):
        assert await _run_offloop(lambda a, b: a + b, 2, 3) == 5

    async def test_propagates_worker_exception(self):
        def _boom():
            raise ValueError("worker failed")

        with pytest.raises(ValueError, match="worker failed"):
            await _run_offloop(_boom)

    async def test_cancellation_waits_for_worker_to_finish(self):
        started = threading.Event()
        finished = threading.Event()

        def _slow():
            started.set()
            # Simulate a blocking write already in flight on the worker thread.
            time.sleep(0.2)
            finished.set()

        task = asyncio.ensure_future(_run_offloop(_slow))
        # Let the worker actually start before we cancel.
        while not started.is_set():
            await asyncio.sleep(0.01)
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        # The worker must have run to completion, not been abandoned mid-flight.
        assert finished.is_set(), (
            "cancellation abandoned the worker before it finished"
        )


class TestScaffoldingCancellationSafety:
    """A cancelled or failed generation must not leak its scaffold directory.

    Before the write hops were offloaded there was no cancellation point once
    scaffolding began, so the directory always either fully materialised (and
    its path was returned) or was never created. Offloading introduced ``await``
    points; ``generate_project`` therefore has to clean up a directory whose
    path it will never hand back.
    """

    async def test_cancelled_generation_removes_orphan_scaffold(
        self, monkeypatch, tmp_path
    ):
        import youtube_extension.backend.code_generator as cg_module

        project_dir = tmp_path / "uvai_project_cancel"
        monkeypatch.setattr(
            cg_module.tempfile, "mkdtemp", _tempdir_factory(project_dir)
        )

        started = threading.Event()
        release = threading.Event()
        real_apply = cg_module._apply_write_plan

        def _blocking_apply(plan):
            # Park the worker mid-scaffold so we can cancel while it "writes".
            started.set()
            release.wait(5)
            real_apply(plan)

        monkeypatch.setattr(cg_module, "_apply_write_plan", _blocking_apply)

        gen = ProjectCodeGenerator(use_ai_generation=False)
        task = asyncio.ensure_future(
            gen.generate_project(
                _build_video_analysis("T", "auJzb1D-fag", "S", []),
                {"project_type": "web", "technologies": ["react"]},
            )
        )

        while not started.is_set():
            await asyncio.sleep(0.01)
        task.cancel()
        # Cancellation is now in flight; let the shielded worker finish so the
        # filesystem is settled before cleanup runs.
        release.set()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert not project_dir.exists(), (
            "cancelled generation leaked its scaffold directory"
        )

    async def test_failed_generation_removes_orphan_scaffold(
        self, monkeypatch, tmp_path
    ):
        import youtube_extension.backend.code_generator as cg_module

        project_dir = tmp_path / "uvai_project_fail"
        monkeypatch.setattr(
            cg_module.tempfile, "mkdtemp", _tempdir_factory(project_dir)
        )

        def _exploding_apply(plan):
            raise RuntimeError("disk exploded")

        monkeypatch.setattr(cg_module, "_apply_write_plan", _exploding_apply)

        gen = ProjectCodeGenerator(use_ai_generation=False)
        with pytest.raises(RuntimeError, match="disk exploded"):
            await gen.generate_project(
                _build_video_analysis("T", "auJzb1D-fag", "S", []),
                {"project_type": "web", "technologies": ["react"]},
            )

        assert not project_dir.exists(), (
            "failed generation leaked its scaffold directory"
        )
