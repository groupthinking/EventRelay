"""Tests for the lightweight project code generator."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

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


def test_build_plan_steps_flow_into_generated_assets(monkeypatch, tmp_path) -> None:
    """BuildPlan steps should drive tutorial content for downstream stages."""

    project_dir = tmp_path / "uvai_build_plan_project"
    project_dir.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

    build_plan = {
        "title": "Weather dashboard build plan",
        "summary": "Structured plan from tutorial",
        "prerequisites": ["node", "react"],
        "steps": [
            {
                "step_number": 1,
                "action": "create_component",
                "description": "Create WeatherCard component to display current conditions",
                "target_file": "src/components/WeatherCard.js",
                "code": "export const WeatherCard = () => null;",
                "dependencies": [],
                "prerequisites": ["react"],
            },
            {
                "step_number": 2,
                "action": "install_dependency",
                "description": "Install axios for API calls",
                "target_file": "package.json",
                "code": "npm install axios",
                "dependencies": [1],
                "prerequisites": ["npm"],
            },
        ],
    }

    generator = ProjectCodeGenerator()
    video_analysis = {
        "metadata": {"title": "Structured Weather App", "keywords": ["react", "weather"]},
        "ai_analysis": {"Related Topics": ["react", "weather api"]},
        "build_plan": build_plan,
        "success": True,
    }
    project_config = {"type": "web", "features": ["api_integration"]}

    result = asyncio.run(generator.generate_project(video_analysis, project_config))
    generated_path = Path(result["project_path"])

    readme_text = (generated_path / "README.md").read_text()
    assert "WeatherCard component" in readme_text
    assert "Install axios" in readme_text

    app_text = (generated_path / "src" / "App.js").read_text()
    assert "WeatherCard component" in app_text
