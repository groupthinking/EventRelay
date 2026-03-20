"""Tests for the lightweight project code generator."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

from youtube_extension.backend.code_generator import ProjectCodeGenerator


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


def test_vanilla_main_js_includes_tutorial_steps_and_features(monkeypatch, tmp_path) -> None:
    """Vanilla JS main.js must reflect video-specific tutorial steps and features."""

    project_dir = tmp_path / "uvai_vanilla_project"
    project_dir.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

    generator = ProjectCodeGenerator()
    video_analysis = {
        "metadata": {"title": "Vanilla JS DOM Tutorial"},
        "ai_analysis": {
            "Content Summary": "Learn DOM manipulation with vanilla JavaScript.",
            "Key Concepts": ["DOM", "events", "selectors"],
            "Learning Path": "Select elements\nAdd event listeners\nManipulate DOM",
        },
        "transcript": {"text": "Select elements. Add event listeners. Manipulate the DOM."},
        "success": True,
    }
    project_config = {
        "type": "web",
        "features": ["dom_manipulation", "event_handling"],
    }

    result = asyncio.run(generator.generate_project(video_analysis, project_config))
    generated_path = Path(result["project_path"])

    main_js = (generated_path / "main.js").read_text()

    # Tutorial steps should be embedded in the generated JS
    assert "Select elements" in main_js or "tutorialSteps" in main_js
    # Feature initialisation stubs should be generated
    assert "dom_manipulation" in main_js or "initDomManipulation" in main_js or "dom manipulation" in main_js
    # Must not be the hardcoded placeholder anymore
    assert "Add interactive features based on video analysis" not in main_js


def test_two_different_videos_produce_different_code(monkeypatch, tmp_path) -> None:
    """Processing two different videos must yield meaningfully different outputs."""

    def make_project_dir(name: str) -> Path:
        d = tmp_path / name
        d.mkdir()
        return d

    dirs: list[Path] = []

    def mkdtemp_side_effect(prefix: str = "") -> str:
        d = make_project_dir(f"proj_{len(dirs)}")
        dirs.append(d)
        return str(d)

    monkeypatch.setattr(tempfile, "mkdtemp", mkdtemp_side_effect)

    generator = ProjectCodeGenerator()

    video_a = {
        "metadata": {"title": "Python FastAPI Tutorial"},
        "ai_analysis": {
            "Content Summary": "Build a REST API with FastAPI and SQLAlchemy.",
            "Key Concepts": ["FastAPI", "REST", "SQLAlchemy"],
            "Learning Path": "Install FastAPI\nCreate endpoints\nConnect database",
        },
        "transcript": {"text": "Install FastAPI. Create endpoints. Connect a database."},
        "success": True,
    }
    config_a = {"type": "api", "features": ["database"]}

    video_b = {
        "metadata": {"title": "CSS Grid Layout Masterclass"},
        "ai_analysis": {
            "Content Summary": "Master CSS grid with practical layout examples.",
            "Key Concepts": ["grid", "columns", "responsive"],
            "Learning Path": "Define grid container\nSet columns\nPlace items",
        },
        "transcript": {"text": "Define a grid container. Set columns and rows. Place grid items."},
        "success": True,
    }
    config_b = {"type": "web", "features": ["responsive_design"]}

    result_a = asyncio.run(generator.generate_project(video_a, config_a))
    result_b = asyncio.run(generator.generate_project(video_b, config_b))

    readme_a = (Path(result_a["project_path"]) / "README.md").read_text()
    readme_b = (Path(result_b["project_path"]) / "README.md").read_text()

    assert "Python FastAPI Tutorial" in readme_a
    assert "CSS Grid Layout Masterclass" in readme_b
    # The two READMEs must not be identical
    assert readme_a != readme_b


def test_generate_repo_name_uses_video_title() -> None:
    """_generate_repo_name should derive the name from the project title, not a generic fallback."""
    pytest.importorskip("aiohttp", reason="aiohttp required for deployment_manager")
    from youtube_extension.backend.deployment_manager import DeploymentManager

    manager = DeploymentManager(github_token=None)

    config_with_title = {"title": "My Awesome Django Tutorial"}
    name = manager._generate_repo_name(config_with_title)
    assert "my-awesome-django-tutorial" in name
    assert "uvai-project" not in name

    config_no_title: dict = {}
    fallback_name = manager._generate_repo_name(config_no_title)
    assert fallback_name.startswith("uvai-project-")

