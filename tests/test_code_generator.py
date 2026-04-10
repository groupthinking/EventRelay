"""Tests for the lightweight project code generator."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from youtube_extension.backend.code_generator import ProjectCodeGenerator


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

    generator = ProjectCodeGenerator()
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

    generator = ProjectCodeGenerator()
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

    generator = ProjectCodeGenerator()
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
