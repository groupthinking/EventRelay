"""
Tests to verify that different videos produce different code outputs.
Addresses issue: code_generator.py falls back to identical vanilla template for every video
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from youtube_extension.backend.code_generator import ProjectCodeGenerator


def test_different_videos_produce_different_vanilla_js(monkeypatch, tmp_path) -> None:
    """Ensure two different videos produce meaningfully different vanilla JS code."""

    # Video 1: JavaScript Todo App (forces vanilla JS)
    project_dir_1 = tmp_path / "project_1"
    project_dir_1.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir_1))

    generator = ProjectCodeGenerator()
    video_analysis_1 = {
        "metadata": {"title": "Build JavaScript Todo App", "keywords": ["javascript", "html"]},
        "ai_analysis": {
            "Content Summary": "Build a simple todo list with vanilla JavaScript.",
            "Related Topics": ["javascript", "html", "css", "dom manipulation"],
            "Key Concepts": ["event listeners", "DOM manipulation", "local storage"],
            "Learning Path": "Create HTML structure\nAdd event listeners\nImplement todo logic",
        },
        "transcript": {"text": "Create HTML structure. Add event listeners. Implement todo logic."},
        "success": True,
    }
    project_config_1 = {"type": "web", "features": ["responsive_design"]}

    result_1 = asyncio.run(generator.generate_project(video_analysis_1, project_config_1))
    path_1 = Path(result_1["project_path"])

    # Video 2: JavaScript Calculator (forces vanilla JS)
    project_dir_2 = tmp_path / "project_2"
    project_dir_2.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir_2))

    generator_2 = ProjectCodeGenerator()
    video_analysis_2 = {
        "metadata": {"title": "Create JavaScript Calculator", "keywords": ["javascript", "math"]},
        "ai_analysis": {
            "Content Summary": "Build a calculator using vanilla JavaScript and CSS Grid.",
            "Related Topics": ["javascript", "css grid", "math operations"],
            "Key Concepts": ["calculator logic", "CSS grid layout", "operator precedence"],
            "Learning Path": "Build calculator UI\nImplement math functions\nAdd keyboard support",
        },
        "transcript": {"text": "Build calculator UI. Implement math functions. Add keyboard support."},
        "success": True,
    }
    project_config_2 = {"type": "web", "features": ["api_integration"]}

    result_2 = asyncio.run(generator_2.generate_project(video_analysis_2, project_config_2))
    path_2 = Path(result_2["project_path"])

    # Verify different titles in HTML
    html_1 = (path_1 / "index.html").read_text()
    html_2 = (path_2 / "index.html").read_text()

    assert "Build JavaScript Todo App" in html_1 or "JavaScript Todo App" in html_1
    assert "Create JavaScript Calculator" in html_2 or "JavaScript Calculator" in html_2
    assert "Calculator" not in html_1
    assert "Todo" not in html_2

    # Verify different tutorial steps in HTML
    assert "event listeners" in html_1.lower() or "todo logic" in html_1.lower()
    assert "calculator" in html_2.lower() or "math functions" in html_2.lower()

    # Verify different key concepts
    assert "dom manipulation" in html_1.lower() or "local storage" in html_1.lower()
    assert "css grid" in html_2.lower() or "operator precedence" in html_2.lower()

    # Verify different JavaScript code
    js_1 = (path_1 / "main.js").read_text()
    js_2 = (path_2 / "main.js").read_text()

    # Different tutorial step comments
    assert "Tutorial Steps from Video" in js_1
    assert "Tutorial Steps from Video" in js_2
    assert "todo logic" in js_1.lower() or "event listeners" in js_1.lower()
    assert "calculator" in js_2.lower() or "math functions" in js_2.lower()

    # Video 1 should have responsive design features
    assert "responsive" in js_1.lower() or "resize" in js_1.lower()
    # Video 2 should have API integration features
    assert "api_integration" in js_2.lower() or "fetchData" in js_2

    # Verify different feature arrays in JS
    assert '["responsive_design"]' in js_1 or "responsive_design" in js_1
    assert '["api_integration"]' in js_2 or "api_integration" in js_2

    # Verify README is different
    readme_1 = (path_1 / "README.md").read_text()
    readme_2 = (path_2 / "README.md").read_text()

    assert "Todo" in readme_1 or "todo" in readme_1
    assert "Calculator" in readme_2
    assert readme_1 != readme_2


def test_react_projects_differ_by_video_content(monkeypatch, tmp_path) -> None:
    """Ensure React projects generated from different videos have unique content."""

    # Video 1: E-commerce with authentication
    project_dir_1 = tmp_path / "ecommerce"
    project_dir_1.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir_1))

    generator = ProjectCodeGenerator()
    video_analysis_1 = {
        "metadata": {"title": "Build E-commerce Site with Auth"},
        "ai_analysis": {
            "Content Summary": "Complete e-commerce platform with user authentication.",
            "Related Topics": ["react", "authentication", "stripe", "shopping cart"],
            "Key Concepts": ["JWT tokens", "protected routes", "payment processing"],
        },
        "transcript": {"text": "Set up authentication. Build product catalog. Add shopping cart."},
        "success": True,
    }
    project_config_1 = {"type": "web", "features": ["authentication", "api_integration"]}

    result_1 = asyncio.run(generator.generate_project(video_analysis_1, project_config_1))
    path_1 = Path(result_1["project_path"])

    # Video 2: Blog platform
    project_dir_2 = tmp_path / "blog"
    project_dir_2.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir_2))

    generator_2 = ProjectCodeGenerator()
    video_analysis_2 = {
        "metadata": {"title": "Create a Blog Platform"},
        "ai_analysis": {
            "Content Summary": "Build a markdown-based blog with search.",
            "Related Topics": ["react", "markdown", "search", "seo"],
            "Key Concepts": ["markdown parsing", "full-text search", "SEO optimization"],
        },
        "transcript": {"text": "Parse markdown. Implement search. Add SEO tags."},
        "success": True,
    }
    project_config_2 = {"type": "web", "features": ["responsive_design"]}

    result_2 = asyncio.run(generator_2.generate_project(video_analysis_2, project_config_2))
    path_2 = Path(result_2["project_path"])

    # Verify different content in App.js
    app_1 = (path_1 / "src" / "App.js").read_text()
    app_2 = (path_2 / "src" / "App.js").read_text()

    # Different titles
    assert "E-commerce Site with Auth" in app_1
    assert "Blog Platform" in app_2

    # Different key concepts
    assert "JWT tokens" in app_1 or "protected routes" in app_1 or "payment processing" in app_1
    assert "markdown parsing" in app_2 or "full-text search" in app_2 or "SEO optimization" in app_2

    # Verify different package.json dependencies based on features
    package_1 = (path_1 / "package.json").read_text()
    package_2 = (path_2 / "package.json").read_text()

    # E-commerce project should have authentication dependencies
    assert "auth" in package_1.lower()
    # Different project names
    assert "ecommerce" in package_1.lower() or "auth" in package_1.lower()
    assert "blog" in package_2.lower()
