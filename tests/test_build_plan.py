"""Tests for Stage 2 Semantic Logic Parsing — BuildPlan extraction."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest

from youtube_extension.backend.build_plan import (
    BuildPlan,
    BuildStep,
    SemanticParser,
    build_gemini_prompt,
    parse_build_plan,
)
from youtube_extension.backend.code_generator import ProjectCodeGenerator


# ---------------------------------------------------------------------------
# BuildStep / BuildPlan round-trip
# ---------------------------------------------------------------------------


def test_build_step_to_dict_round_trip() -> None:
    step = BuildStep(
        order=1,
        action="create",
        target_file="src/App.js",
        description="Create the main React component",
        code_content="function App() { return <div>Hello</div>; }",
        dependencies=["react"],
    )
    d = step.to_dict()
    assert d["order"] == 1
    assert d["action"] == "create"
    assert d["target_file"] == "src/App.js"
    assert d["dependencies"] == ["react"]

    restored = BuildStep.from_dict(d)
    assert restored.order == step.order
    assert restored.action == step.action
    assert restored.target_file == step.target_file
    assert restored.code_content == step.code_content
    assert restored.dependencies == step.dependencies


def test_build_plan_to_dict_round_trip() -> None:
    plan = BuildPlan(
        title="Weather App",
        project_type="web",
        technologies=["react", "tailwind"],
        steps=[
            BuildStep(order=1, action="create", target_file="package.json", description="Init project"),
            BuildStep(order=2, action="install", target_file="", description="Install react"),
        ],
        summary="A weather dashboard built with React.",
    )
    d = plan.to_dict()
    assert d["title"] == "Weather App"
    assert d["project_type"] == "web"
    assert len(d["steps"]) == 2
    assert d["steps"][0]["order"] == 1

    restored = BuildPlan.from_dict(d)
    assert restored.title == plan.title
    assert len(restored.steps) == 2
    assert restored.steps[1].action == "install"


# ---------------------------------------------------------------------------
# SemanticParser strategies
# ---------------------------------------------------------------------------


def _base_video_analysis(**kwargs) -> dict:
    base = {
        "metadata": {"title": "Build a React Weather App", "channel": "TechTuts", "duration": "15:00"},
        "ai_analysis": {
            "Content Summary": "Walks through building a weather dashboard with React hooks.",
            "Related Topics": ["react", "hooks", "api integration"],
            "Key Concepts": ["state management", "effects", "api calls"],
            "Learning Path": "Set up React\nFetch weather data\nRender dashboard",
        },
        "transcript": {"text": "Set up React. Fetch weather data. Render dashboard components."},
        "success": True,
    }
    base.update(kwargs)
    return base


def test_semantic_parser_strategy1_embedded_build_plan() -> None:
    """Parser uses an embedded build_plan from ai_analysis when present."""
    embedded_plan = {
        "title": "Weather Dashboard",
        "project_type": "web",
        "technologies": ["react"],
        "summary": "Build a weather dashboard",
        "steps": [
            {"order": 1, "action": "create", "target_file": "package.json", "description": "Init", "code_content": "", "dependencies": []},
            {"order": 2, "action": "implement", "target_file": "src/App.js", "description": "Main component", "code_content": "", "dependencies": ["react"]},
        ],
    }
    video_analysis = _base_video_analysis()
    video_analysis["ai_analysis"]["build_plan"] = embedded_plan

    plan = SemanticParser().parse(video_analysis)
    assert plan.title == "Weather Dashboard"
    assert len(plan.steps) == 2
    assert plan.steps[0].action == "create"
    assert plan.steps[1].target_file == "src/App.js"


def test_semantic_parser_strategy1_embedded_plan_as_json_string() -> None:
    """Parser handles an embedded build_plan stored as a JSON string."""
    embedded_plan = {
        "title": "API Server",
        "project_type": "api",
        "technologies": ["fastapi"],
        "summary": "A FastAPI server",
        "steps": [
            {"order": 1, "action": "create", "target_file": "main.py", "description": "Entry point", "code_content": "", "dependencies": []},
        ],
    }
    video_analysis = _base_video_analysis()
    video_analysis["ai_analysis"]["build_plan"] = json.dumps(embedded_plan)

    plan = SemanticParser().parse(video_analysis)
    assert plan.project_type == "api"
    assert plan.steps[0].target_file == "main.py"


def test_semantic_parser_strategy2_learning_path() -> None:
    """Parser derives ordered steps from Learning Path when no build_plan present."""
    video_analysis = _base_video_analysis()
    # Remove any embedded build_plan
    video_analysis["ai_analysis"].pop("build_plan", None)

    plan = SemanticParser().parse(video_analysis)
    assert len(plan.steps) >= 3
    # Steps should map to the lines in Learning Path
    descriptions = [s.description for s in plan.steps]
    assert any("React" in d for d in descriptions)


def test_semantic_parser_strategy3_transcript() -> None:
    """Parser falls back to transcript when no Learning Path is available."""
    video_analysis = _base_video_analysis()
    video_analysis["ai_analysis"].pop("Learning Path", None)
    video_analysis["ai_analysis"].pop("build_plan", None)
    video_analysis["transcript"] = {"text": "Install react. Create App component. Fetch weather data. Add styling."}

    plan = SemanticParser().parse(video_analysis)
    assert len(plan.steps) >= 1


def test_semantic_parser_strategy4_technology_fallback() -> None:
    """Parser produces a minimal plan from technologies when nothing else is available."""
    plan = SemanticParser().parse({
        "metadata": {"title": "Vue Tutorial"},
        "ai_analysis": {},
        "transcript": {},
    })
    assert len(plan.steps) > 0


def test_semantic_parser_preserves_step_ordering() -> None:
    """Steps in the resulting plan are ordered correctly (1-based)."""
    video_analysis = _base_video_analysis()
    plan = SemanticParser().parse(video_analysis)
    for i, step in enumerate(plan.steps, start=1):
        assert step.order == i


# ---------------------------------------------------------------------------
# parse_build_plan convenience wrapper
# ---------------------------------------------------------------------------


def test_parse_build_plan_returns_build_plan_instance() -> None:
    plan = parse_build_plan(_base_video_analysis())
    assert isinstance(plan, BuildPlan)
    assert len(plan.steps) > 0


# ---------------------------------------------------------------------------
# build_gemini_prompt
# ---------------------------------------------------------------------------


def test_build_gemini_prompt_includes_metadata() -> None:
    metadata = {"title": "React Tutorial", "channel": "CodeAcademy", "duration": "20:00"}
    transcript = "First we create the project. Then we install dependencies."
    prompt = build_gemini_prompt(metadata, transcript)
    assert "React Tutorial" in prompt
    assert "CodeAcademy" in prompt
    # The standalone prompt asks for a build plan (steps at top level)
    assert "steps" in prompt
    assert "action" in prompt


# ---------------------------------------------------------------------------
# Integration: ProjectCodeGenerator includes build_plan in result
# ---------------------------------------------------------------------------


def test_generate_project_includes_build_plan(monkeypatch, tmp_path) -> None:
    """generate_project result must contain a 'build_plan' dict with 'steps'."""
    project_dir = tmp_path / "uvai_generated"
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

    assert "build_plan" in result, "Result must contain a build_plan artifact"
    bp = result["build_plan"]
    assert "steps" in bp, "build_plan must have 'steps'"
    assert len(bp["steps"]) > 0, "build_plan must have at least one step"

    # Each step must have the required fields
    required_fields = {"order", "action", "target_file", "description", "code_content", "dependencies"}
    for step in bp["steps"]:
        missing = required_fields - set(step.keys())
        assert not missing, f"Step missing fields: {missing}"


def test_generate_project_steps_ordered(monkeypatch, tmp_path) -> None:
    """Steps in the build_plan must be in ascending order."""
    project_dir = tmp_path / "uvai_ordered"
    project_dir.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

    generator = ProjectCodeGenerator()
    video_analysis = {
        "metadata": {"title": "Vue App"},
        "ai_analysis": {
            "Learning Path": "Install Vue\nCreate main component\nAdd routing\nDeploy",
        },
        "transcript": {"text": ""},
        "success": True,
    }
    result = asyncio.run(generator.generate_project(video_analysis, {"type": "web"}))
    steps = result["build_plan"]["steps"]
    orders = [s["order"] for s in steps]
    assert orders == sorted(orders)


def test_build_plan_embedded_from_ai_analysis_end_to_end(monkeypatch, tmp_path) -> None:
    """When ai_analysis contains a build_plan, generator uses it verbatim."""
    project_dir = tmp_path / "uvai_embedded"
    project_dir.mkdir()
    monkeypatch.setattr(tempfile, "mkdtemp", lambda prefix: str(project_dir))

    embedded_plan = {
        "title": "Todo App",
        "project_type": "web",
        "technologies": ["react"],
        "summary": "A simple React todo list",
        "steps": [
            {"order": 1, "action": "create", "target_file": "package.json", "description": "Init npm", "code_content": "", "dependencies": []},
            {"order": 2, "action": "install", "target_file": "", "description": "npm install react", "code_content": "", "dependencies": []},
            {"order": 3, "action": "implement", "target_file": "src/App.js", "description": "TodoApp component", "code_content": "function App() {}", "dependencies": ["react"]},
        ],
    }

    generator = ProjectCodeGenerator()
    video_analysis = {
        "metadata": {"title": "React Todo Tutorial"},
        "ai_analysis": {"build_plan": embedded_plan},
        "transcript": {"text": "Build a todo app with React."},
        "success": True,
    }
    result = asyncio.run(generator.generate_project(video_analysis, {"type": "web"}))
    bp = result["build_plan"]
    assert bp["title"] == "Todo App"
    assert len(bp["steps"]) == 3
    assert bp["steps"][2]["code_content"] == "function App() {}"
