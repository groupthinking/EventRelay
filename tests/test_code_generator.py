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


def test_vanilla_project_renders_tutorial_steps(tmp_path) -> None:
    """Vanilla projects should still reflect tutorial-specific details."""

    generator = ProjectCodeGenerator()
    video_analysis = {
        "metadata": {"title": "HTML Landing Page Tutorial", "keywords": ["html", "css"]},
        "extracted_info": {
            "title": "HTML Landing Page Tutorial",
            "technologies": ["HTML", "CSS", "JavaScript"],
            "tutorial_steps": ["Setup HTML structure", "Add hero section", "Deploy to Netlify"],
            "features": ["responsive_design"],
        },
        "ai_analysis": {"Key Concepts": ["semantic html", "layout"]},
    }
    project_config = {"type": "web", "features": ["responsive_design"], "title": "HTML Landing Page Tutorial"}

    result = asyncio.run(generator.generate_project(video_analysis, project_config))
    generated_path = Path(result["project_path"])

    main_js = (generated_path / "main.js").read_text()
    assert "Setup HTML structure" in main_js
    assert "Add hero section" in main_js

    index_html = (generated_path / "index.html").read_text()
    assert "feature-cards dynamic" in index_html
    assert "tech-cards dynamic" in index_html

    assert generated_path.name.startswith("html-landing-page-tutorial")
