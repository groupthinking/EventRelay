"""Unit tests for build_plan module: StepAction, BuildStep, BuildPlan."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from youtube_extension.backend.models.build_plan import (
    BuildPlan,
    BuildStep,
    StepAction,
)


# ===========================================================================
# StepAction enum
# ===========================================================================


class TestStepActionEnum:
    def test_create_file_value(self):
        assert StepAction.CREATE_FILE.value == "create_file"

    def test_modify_file_value(self):
        assert StepAction.MODIFY_FILE.value == "modify_file"

    def test_install_dependency_value(self):
        assert StepAction.INSTALL_DEPENDENCY.value == "install_dependency"

    def test_run_command_value(self):
        assert StepAction.RUN_COMMAND.value == "run_command"

    def test_configure_value(self):
        assert StepAction.CONFIGURE.value == "configure"

    def test_deploy_value(self):
        assert StepAction.DEPLOY.value == "deploy"

    def test_has_six_members(self):
        assert len(StepAction) == 6


# ===========================================================================
# BuildStep model
# ===========================================================================


class TestBuildStep:
    @pytest.fixture
    def step(self):
        return BuildStep(
            order=1,
            action=StepAction.CREATE_FILE,
            description="Create the main file",
        )

    def test_order_stored(self, step):
        assert step.order == 1

    def test_action_stored(self, step):
        assert step.action == StepAction.CREATE_FILE

    def test_description_stored(self, step):
        assert step.description == "Create the main file"

    def test_target_file_defaults_none(self, step):
        assert step.target_file is None

    def test_code_content_defaults_none(self, step):
        assert step.code_content is None

    def test_dependencies_defaults_empty_list(self, step):
        assert step.dependencies == []

    def test_prerequisites_defaults_empty_list(self, step):
        assert step.prerequisites == []

    def test_target_file_set(self):
        s = BuildStep(order=2, action=StepAction.MODIFY_FILE, description="Edit", target_file="main.py")
        assert s.target_file == "main.py"

    def test_dependencies_set(self):
        s = BuildStep(order=1, action=StepAction.INSTALL_DEPENDENCY, description="Install", dependencies=["flask"])
        assert s.dependencies == ["flask"]

    def test_prerequisites_set(self):
        s = BuildStep(order=3, action=StepAction.RUN_COMMAND, description="Run", prerequisites=[1, 2])
        assert s.prerequisites == [1, 2]


# ===========================================================================
# BuildPlan model
# ===========================================================================


def _file_step(order: int) -> BuildStep:
    return BuildStep(order=order, action=StepAction.CREATE_FILE, description=f"Create {order}")


def _modify_step(order: int) -> BuildStep:
    return BuildStep(order=order, action=StepAction.MODIFY_FILE, description=f"Modify {order}")


def _dep_step(order: int) -> BuildStep:
    return BuildStep(order=order, action=StepAction.INSTALL_DEPENDENCY, description=f"Install {order}")


def _run_step(order: int) -> BuildStep:
    return BuildStep(order=order, action=StepAction.RUN_COMMAND, description=f"Run {order}")


class TestBuildPlanDefaults:
    @pytest.fixture
    def plan(self):
        return BuildPlan(video_id="abc123", video_title="Test Video")

    def test_video_id_stored(self, plan):
        assert plan.video_id == "abc123"

    def test_video_title_stored(self, plan):
        assert plan.video_title == "Test Video"

    def test_project_type_default_web(self, plan):
        assert plan.project_type == "web"

    def test_framework_default_none(self, plan):
        assert plan.framework is None

    def test_technologies_default_empty(self, plan):
        assert plan.technologies == []

    def test_steps_default_empty(self, plan):
        assert plan.steps == []

    def test_summary_default_empty_string(self, plan):
        assert plan.summary == ""


class TestBuildPlanFileSteps:
    def test_returns_only_create_and_modify_steps(self):
        plan = BuildPlan(
            video_id="x",
            video_title="T",
            steps=[
                _file_step(1),
                _dep_step(2),
                _modify_step(3),
                _run_step(4),
            ],
        )
        file_steps = plan.file_steps
        assert len(file_steps) == 2
        assert all(s.action in (StepAction.CREATE_FILE, StepAction.MODIFY_FILE) for s in file_steps)

    def test_empty_steps_returns_empty(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[])
        assert plan.file_steps == []

    def test_only_install_steps_returns_empty(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[_dep_step(1)])
        assert plan.file_steps == []

    def test_create_step_included(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[_file_step(1)])
        assert len(plan.file_steps) == 1
        assert plan.file_steps[0].action == StepAction.CREATE_FILE

    def test_modify_step_included(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[_modify_step(1)])
        assert len(plan.file_steps) == 1
        assert plan.file_steps[0].action == StepAction.MODIFY_FILE


class TestBuildPlanDependencySteps:
    def test_returns_only_install_steps(self):
        plan = BuildPlan(
            video_id="x",
            video_title="T",
            steps=[_file_step(1), _dep_step(2), _run_step(3)],
        )
        dep_steps = plan.dependency_steps
        assert len(dep_steps) == 1
        assert dep_steps[0].action == StepAction.INSTALL_DEPENDENCY

    def test_empty_steps_returns_empty(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[])
        assert plan.dependency_steps == []

    def test_no_install_steps_returns_empty(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[_file_step(1), _run_step(2)])
        assert plan.dependency_steps == []

    def test_multiple_install_steps(self):
        plan = BuildPlan(video_id="x", video_title="T", steps=[_dep_step(1), _dep_step(2)])
        assert len(plan.dependency_steps) == 2


class TestBuildPlanGeminiSchema:
    def test_returns_dict(self):
        plan = BuildPlan(video_id="x", video_title="T")
        schema = plan.gemini_schema()
        assert isinstance(schema, dict)

    def test_schema_has_title_or_type(self):
        plan = BuildPlan(video_id="x", video_title="T")
        schema = plan.gemini_schema()
        assert "type" in schema
        assert schema["type"] == "object"

    def test_schema_is_reproducible(self):
        plan = BuildPlan(video_id="x", video_title="T")
        assert plan.gemini_schema() == plan.gemini_schema()


class TestBuildPlanCustomFields:
    def test_project_type_custom(self):
        plan = BuildPlan(video_id="x", video_title="T", project_type="api")
        assert plan.project_type == "api"

    def test_framework_set(self):
        plan = BuildPlan(video_id="x", video_title="T", framework="fastapi")
        assert plan.framework == "fastapi"

    def test_technologies_set(self):
        plan = BuildPlan(video_id="x", video_title="T", technologies=["Python", "FastAPI"])
        assert plan.technologies == ["Python", "FastAPI"]

    def test_summary_set(self):
        plan = BuildPlan(video_id="x", video_title="T", summary="Builds a REST API")
        assert plan.summary == "Builds a REST API"
