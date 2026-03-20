#!/usr/bin/env python3
"""
Tests for code_generator.py — verifying unique output per video.

Run: python -m pytest tests/test_code_generator_unique_output.py -v
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root so imports resolve
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pytest

# Disable AI generation for unit tests (no API key needed)
os.environ.pop("GEMINI_API_KEY", None)

from youtube_extension.backend.code_generator import ProjectCodeGenerator


@pytest.fixture
def generator():
    """Create a code generator with AI disabled for deterministic tests."""
    return ProjectCodeGenerator(use_ai_generation=False)


def _make_video_analysis(video_id: str, title: str, technologies: list, summary: str = "", steps: list = None):
    """Helper to build a realistic video_analysis dict."""
    return {
        "video_data": {"video_id": video_id, "video_url": f"https://youtube.com/watch?v={video_id}"},
        "metadata": {"title": title, "keywords": technologies},
        "extracted_info": {
            "title": title,
            "technologies": technologies,
            "features": ["responsive_design"],
            "tutorial_steps": steps or [f"Step {i} for {title}" for i in range(1, 4)],
            "project_type": "web",
        },
        "ai_analysis": {
            "Content Summary": summary or f"This tutorial covers {title}.",
            "Key Concepts": technologies[:5],
        },
        "summary": summary or f"This tutorial covers {title}.",
        "key_concepts": technologies[:5],
    }


@pytest.mark.asyncio
async def test_different_videos_produce_different_js(generator):
    """Two different videos should produce different main.js content."""
    analysis_a = _make_video_analysis("abc123", "Build a Todo App with React", ["react", "javascript", "css"])
    analysis_b = _make_video_analysis("xyz789", "Machine Learning with Python", ["python", "tensorflow", "numpy"])

    config_a = {"type": "web", "features": ["responsive_design"], "title": "Build a Todo App with React"}
    config_b = {"type": "web", "features": ["responsive_design"], "title": "Machine Learning with Python"}

    result_a = await generator.generate_project(analysis_a, config_a)
    result_b = await generator.generate_project(analysis_b, config_b)

    path_a = Path(result_a["project_path"])
    path_b = Path(result_b["project_path"])

    # Read main.js (or App.js for react) from each
    js_a = _read_js(path_a, result_a)
    js_b = _read_js(path_b, result_b)

    assert js_a != js_b, "main.js should differ between two different videos"


@pytest.mark.asyncio
async def test_different_videos_produce_different_css(generator):
    """Two different videos should produce different styles.css (accent color)."""
    analysis_a = _make_video_analysis("abc123", "Build a REST API", ["python", "fastapi"])
    analysis_b = _make_video_analysis("def456", "CSS Animations Masterclass", ["css", "javascript"])

    config_a = {"type": "web", "features": [], "title": "Build a REST API"}
    config_b = {"type": "web", "features": [], "title": "CSS Animations Masterclass"}

    result_a = await generator.generate_project(analysis_a, config_a)
    result_b = await generator.generate_project(analysis_b, config_b)

    css_a = (Path(result_a["project_path"]) / "styles.css").read_text()
    css_b = (Path(result_b["project_path"]) / "styles.css").read_text()

    assert css_a != css_b, "styles.css should differ (at minimum, different accent color)"


@pytest.mark.asyncio
async def test_same_video_produces_deterministic_output(generator):
    """The same video should produce deterministic (reproducible) output."""
    analysis = _make_video_analysis("same123", "Consistent Build", ["html", "css"])
    config = {"type": "web", "features": [], "title": "Consistent Build"}

    result_1 = await generator.generate_project(analysis, config)
    result_2 = await generator.generate_project(analysis, config)

    js_1 = _read_js(Path(result_1["project_path"]), result_1)
    js_2 = _read_js(Path(result_2["project_path"]), result_2)

    # Fingerprint is deterministic, so structure should match
    # (timestamps will differ, but the fingerprint and content sections should match)
    fp_1 = _extract_fingerprint(js_1)
    fp_2 = _extract_fingerprint(js_2)
    assert fp_1 == fp_2, "Same video should produce the same fingerprint"


@pytest.mark.asyncio
async def test_title_appears_in_all_generated_files(generator):
    """The video title should appear in every generated file."""
    title = "Advanced TypeScript Patterns"
    analysis = _make_video_analysis("ts_patterns", title, ["typescript", "javascript"])
    config = {"type": "web", "features": [], "title": title}

    result = await generator.generate_project(analysis, config)
    path = Path(result["project_path"])

    for fname in result["files_created"]:
        content = (path / fname).read_text()
        assert title in content, f"Title '{title}' should appear in {fname}"


@pytest.mark.asyncio
async def test_fingerprint_is_unique_per_video(generator):
    """Fingerprints derived from different videos must differ."""
    fp_a = ProjectCodeGenerator._video_fingerprint("vid_a", "Title A", ["react"])
    fp_b = ProjectCodeGenerator._video_fingerprint("vid_b", "Title B", ["vue"])
    assert fp_a != fp_b


@pytest.mark.asyncio
async def test_accent_color_varies(generator):
    """Different fingerprints should produce different accent colors."""
    fp_a = ProjectCodeGenerator._video_fingerprint("vid_a", "Title A", ["react"])
    fp_b = ProjectCodeGenerator._video_fingerprint("vid_b", "Title B", ["vue"])
    color_a = ProjectCodeGenerator._accent_from_fingerprint(fp_a)
    color_b = ProjectCodeGenerator._accent_from_fingerprint(fp_b)
    assert color_a != color_b, "Accent colors should differ for different videos"


def _read_js(project_path: Path, result: dict) -> str:
    """Read the JS entry point (main.js or App.js)."""
    for candidate in ["main.js", "src/App.js"]:
        p = project_path / candidate
        if p.exists():
            return p.read_text()
    raise FileNotFoundError(f"No JS file found in {project_path}")


def _extract_fingerprint(js_content: str) -> str:
    """Extract fingerprint from generated JS."""
    for line in js_content.splitlines():
        if "Fingerprint:" in line:
            return line.split("Fingerprint:")[-1].strip()
        if '"fingerprint":' in line or "'fingerprint':" in line:
            return line.split(":")[-1].strip().strip('",')
    return ""
