"""Unit tests for backend/models/build_plan.py — StepAction, BuildStep, BuildPlan."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Import directly from the module file to avoid triggering the
# SQLAlchemy-dependent models/__init__.py.
_BUILD_PLAN_PATH = (
    Path(__file__).resolve().parents[2]
    / "src/youtube_extension/backend/models/build_plan.py"
)
_spec = importlib.util.spec_from_file_location(
    "youtube_extension.backend.models.build_plan", _BUILD_PLAN_PATH
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["youtube_extension.backend.models.build_plan"] = _mod
_spec.loader.exec_module(_mod)
# Pydantic needs model_rebuild() when loaded outside its package context
# because `from __future__ import annotations` defers all type resolution.
_mod.BuildStep.model_rebuild(force=True)
_mod.BuildPlan.model_rebuild(force=True)
BuildPlan = _mod.BuildPlan
BuildStep = _mod.BuildStep
StepAction = _mod.StepAction


# ===========================================================================
# StepAction enum
# ===========================================================================


class TestStepAction:
    def test_all_values_defined(self):
        values = {a.value for a in StepAction}
        assert values == {
            "create_file",
            "modify_file",
            "install_dependency",
            "run_command",
            "configure",
            "deploy",
        }

    def test_str_comparison(self):
        assert StepAction.CREATE_FILE == "create_file"
        assert StepAction.INSTALL_DEPENDENCY == "install_dependency"

    def test_round_trip_from_value(self):
        assert StepAction("run_command") is StepAction.RUN_COMMAND

    def test_invalid_value_raises(self):
        with pytest.raises(ValueError):
            StepAction("nonexistent")


# ===========================================================================
# BuildStep
# ===========================================================================


class TestBuildStep:
    def _minimal(self, **kwargs) -> BuildStep:
        defaults = dict(order=1, action=StepAction.CREATE_FILE, description="Create index.js")
        return BuildStep(**{**defaults, **kwargs})

    def test_minimal_step_valid(self):
        step = self._minimal()
        assert step.order == 1
        assert step.action == StepAction.CREATE_FILE
        assert step.description == "Create index.js"

    def test_defaults_for_optional_fields(self):
        step = self._minimal()
        assert step.target_file is None
        assert step.code_content is None
        assert step.dependencies == []
        assert step.prerequisites == []

    def test_with_target_file(self):
        step = self._minimal(target_file="src/index.js")
        assert step.target_file == "src/index.js"

    def test_with_dependencies(self):
        step = self._minimal(
            action=StepAction.INSTALL_DEPENDENCY,
            dependencies=["react", "react-dom"],
        )
        assert step.dependencies == ["react", "react-dom"]

    def test_with_prerequisites(self):
        step = self._minimal(order=3, prerequisites=[1, 2])
        assert step.prerequisites == [1, 2]

    def test_action_must_be_valid_enum(self):
        with pytest.raises(ValidationError):
            BuildStep(order=1, action="invalid_action", description="x")

    def test_order_required(self):
        with pytest.raises(ValidationError):
            BuildStep(action=StepAction.CONFIGURE, description="x")

    def test_description_required(self):
        with pytest.raises(ValidationError):
            BuildStep(order=1, action=StepAction.DEPLOY)

    def test_all_action_types_accepted(self):
        for action in StepAction:
            step = self._minimal(action=action)
            assert step.action == action


# ===========================================================================
# BuildPlan
# ===========================================================================


class TestBuildPlan:
    def _make_step(self, order: int, action: StepAction) -> BuildStep:
        return BuildStep(order=order, action=action, description=f"Step {order}")

    def test_minimal_plan_valid(self):
        plan = BuildPlan(video_id="abc123", video_title="My Video")
        assert plan.video_id == "abc123"
        assert plan.video_title == "My Video"

    def test_defaults(self):
        plan = BuildPlan(video_id="abc", video_title="T")
        assert plan.project_type == "web"
        assert plan.framework is None
        assert plan.technologies == []
        assert plan.steps == []
        assert plan.summary == ""

    def test_video_id_required(self):
        with pytest.raises(ValidationError):
            BuildPlan(video_title="No ID")

    def test_video_title_required(self):
        with pytest.raises(ValidationError):
            BuildPlan(video_id="abc")

    def test_with_full_data(self):
        plan = BuildPlan(
            video_id="xyz",
            video_title="Build a React App",
            project_type="web",
            framework="react",
            technologies=["react", "typescript", "vite"],
            summary="Tutorial on building a React app from scratch.",
        )
        assert plan.framework == "react"
        assert len(plan.technologies) == 3

    # --- file_steps property ---

    def test_file_steps_returns_create_and_modify(self):
        plan = BuildPlan(
            video_id="v",
            video_title="T",
            steps=[
                self._make_step(1, StepAction.CREATE_FILE),
                self._make_step(2, StepAction.MODIFY_FILE),
                self._make_step(3, StepAction.INSTALL_DEPENDENCY),
                self._make_step(4, StepAction.RUN_COMMAND),
            ],
        )
        assert len(plan.file_steps) == 2
        assert all(s.action in (StepAction.CREATE_FILE, StepAction.MODIFY_FILE) for s in plan.file_steps)

    def test_file_steps_empty_when_no_file_steps(self):
        plan = BuildPlan(
            video_id="v",
            video_title="T",
            steps=[self._make_step(1, StepAction.RUN_COMMAND)],
        )
        assert plan.file_steps == []

    def test_file_steps_empty_plan(self):
        plan = BuildPlan(video_id="v", video_title="T")
        assert plan.file_steps == []

    # --- dependency_steps property ---

    def test_dependency_steps_returns_installs(self):
        plan = BuildPlan(
            video_id="v",
            video_title="T",
            steps=[
                self._make_step(1, StepAction.INSTALL_DEPENDENCY),
                self._make_step(2, StepAction.CREATE_FILE),
                self._make_step(3, StepAction.INSTALL_DEPENDENCY),
            ],
        )
        assert len(plan.dependency_steps) == 2
        assert all(s.action == StepAction.INSTALL_DEPENDENCY for s in plan.dependency_steps)

    def test_dependency_steps_empty_when_none(self):
        plan = BuildPlan(
            video_id="v",
            video_title="T",
            steps=[self._make_step(1, StepAction.CREATE_FILE)],
        )
        assert plan.dependency_steps == []

    # --- gemini_schema ---

    def test_gemini_schema_returns_dict(self):
        plan = BuildPlan(video_id="v", video_title="T")
        schema = plan.gemini_schema()
        assert isinstance(schema, dict)

    def test_gemini_schema_contains_title(self):
        plan = BuildPlan(video_id="v", video_title="T")
        schema = plan.gemini_schema()
        assert "title" in schema or "properties" in schema

    def test_gemini_schema_includes_steps_property(self):
        plan = BuildPlan(video_id="v", video_title="T")
        schema = plan.gemini_schema()
        props = schema.get("properties", {})
        assert "steps" in props
