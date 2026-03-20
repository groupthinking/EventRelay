"""
Tests for BuildPlan Model and Structured Output Schema
=======================================================

Tests Stage 2: Semantic Logic Parsing functionality including:
- BuildPlan Pydantic model validation
- JSON schema generation for Gemini
- Build step ordering and dependencies
"""

import pytest
from pydantic import ValidationError

from youtube_extension.backend.models.build_plan import (
    ActionType,
    BuildPlan,
    BuildStep,
    DifficultyLevel,
    ProjectType,
    build_plan_to_gemini_schema,
)


class TestBuildStep:
    """Tests for BuildStep model."""

    def test_build_step_creation(self):
        """Test creating a valid BuildStep."""
        step = BuildStep(
            step_number=1,
            action=ActionType.CREATE_FILE,
            title="Create React App",
            description="Initialize a new React application",
            command="npx create-react-app my-app",
            dependencies=[],
        )

        assert step.step_number == 1
        assert step.action == ActionType.CREATE_FILE
        assert step.title == "Create React App"
        assert step.command == "npx create-react-app my-app"
        assert step.dependencies == []

    def test_build_step_with_code(self):
        """Test BuildStep with code snippet."""
        step = BuildStep(
            step_number=2,
            action=ActionType.CREATE_COMPONENT,
            title="Create Header Component",
            description="Create a responsive header component",
            target_file="src/components/Header.jsx",
            code_snippet="import React from 'react';\n\nfunction Header() { return <div>Hello</div>; }",
            dependencies=[1],
        )

        assert step.target_file == "src/components/Header.jsx"
        assert "import React" in step.code_snippet
        assert step.dependencies == [1]

    def test_build_step_requires_step_number(self):
        """Test that step_number is required."""
        with pytest.raises(ValidationError):
            BuildStep(
                action=ActionType.CREATE_FILE,
                title="Test",
                description="Test step",
            )

    def test_build_step_invalid_step_number(self):
        """Test that step_number must be >= 1."""
        with pytest.raises(ValidationError):
            BuildStep(
                step_number=0,
                action=ActionType.CREATE_FILE,
                title="Test",
                description="Test step",
            )

    def test_build_step_title_max_length(self):
        """Test that title has max length constraint."""
        long_title = "x" * 101
        with pytest.raises(ValidationError):
            BuildStep(
                step_number=1,
                action=ActionType.CREATE_FILE,
                title=long_title,
                description="Test",
            )


class TestBuildPlan:
    """Tests for BuildPlan model."""

    def test_build_plan_creation(self):
        """Test creating a valid BuildPlan."""
        plan = BuildPlan(
            title="Todo App with React",
            description="Build a simple todo application",
            project_type=ProjectType.REACT,
            technologies=["react", "javascript"],
            steps=[
                BuildStep(
                    step_number=1,
                    action=ActionType.CREATE_FILE,
                    title="Create React App",
                    description="Initialize React app",
                ),
            ],
        )

        assert plan.title == "Todo App with React"
        assert plan.project_type == ProjectType.REACT
        assert len(plan.steps) == 1
        assert plan.difficulty_level == DifficultyLevel.BEGINNER

    def test_build_plan_with_multiple_steps(self):
        """Test BuildPlan with ordered steps and dependencies."""
        plan = BuildPlan(
            title="Full Stack App",
            description="Build a full stack application",
            project_type=ProjectType.NEXTJS,
            difficulty_level=DifficultyLevel.ADVANCED,
            technologies=["nextjs", "typescript", "tailwindcss"],
            features=["authentication", "api", "database"],
            steps=[
                BuildStep(
                    step_number=1,
                    action=ActionType.CREATE_FILE,
                    title="Create Next.js App",
                    description="Initialize Next.js application",
                    dependencies=[],
                ),
                BuildStep(
                    step_number=2,
                    action=ActionType.INSTALL_DEPENDENCY,
                    title="Install Tailwind CSS",
                    description="Add Tailwind CSS for styling",
                    command="npm install -D tailwindcss",
                    dependencies=[1],
                ),
                BuildStep(
                    step_number=3,
                    action=ActionType.CREATE_COMPONENT,
                    title="Create Auth Component",
                    description="Create authentication component",
                    target_file="src/app/auth/page.tsx",
                    dependencies=[2],
                ),
            ],
        )

        assert len(plan.steps) == 3
        assert plan.steps[1].dependencies == [1]
        assert plan.steps[2].dependencies == [2]
        assert plan.difficulty_level == DifficultyLevel.ADVANCED

    def test_build_plan_requires_title(self):
        """Test that title is required."""
        with pytest.raises(ValidationError):
            BuildPlan(
                description="Test",
                project_type=ProjectType.WEB,
                technologies=["javascript"],
                steps=[
                    BuildStep(
                        step_number=1,
                        action=ActionType.CREATE_FILE,
                        title="Test",
                        description="Test",
                    )
                ],
            )

    def test_build_plan_requires_technologies(self):
        """Test that technologies is required."""
        with pytest.raises(ValidationError):
            BuildPlan(
                title="Test App",
                description="Test",
                project_type=ProjectType.WEB,
                technologies=[],  # Empty list should fail min_items=1
                steps=[
                    BuildStep(
                        step_number=1,
                        action=ActionType.CREATE_FILE,
                        title="Test",
                        description="Test",
                    )
                ],
            )

    def test_build_plan_requires_steps(self):
        """Test that steps is required."""
        with pytest.raises(ValidationError):
            BuildPlan(
                title="Test App",
                description="Test",
                project_type=ProjectType.WEB,
                technologies=["javascript"],
                steps=[],  # Empty list should fail min_items=1
            )

    def test_build_plan_with_metadata(self):
        """Test BuildPlan with video metadata."""
        plan = BuildPlan(
            title="Video Tutorial App",
            description="App from video tutorial",
            project_type=ProjectType.REACT,
            technologies=["react"],
            steps=[
                BuildStep(
                    step_number=1,
                    action=ActionType.CREATE_FILE,
                    title="Setup",
                    description="Setup project",
                )
            ],
            video_metadata={
                "video_id": "test123",
                "source_url": "https://youtube.com/watch?v=test123",
                "duration": "15:30",
            },
        )

        assert plan.video_metadata["video_id"] == "test123"
        assert "youtube.com" in plan.video_metadata["source_url"]


class TestGeminiSchema:
    """Tests for Gemini JSON schema generation."""

    def test_schema_generation(self):
        """Test that Gemini schema is generated correctly."""
        schema = build_plan_to_gemini_schema()

        assert schema["type"] == "object"
        assert "title" in schema["properties"]
        assert "steps" in schema["properties"]
        assert "technologies" in schema["properties"]

    def test_schema_required_fields(self):
        """Test that required fields are specified in schema."""
        schema = build_plan_to_gemini_schema()

        assert "required" in schema
        assert "title" in schema["required"]
        assert "description" in schema["required"]
        assert "project_type" in schema["required"]
        assert "technologies" in schema["required"]
        assert "steps" in schema["required"]

    def test_schema_step_properties(self):
        """Test that step schema has correct structure."""
        schema = build_plan_to_gemini_schema()

        step_schema = schema["properties"]["steps"]["items"]
        assert step_schema["type"] == "object"
        assert "step_number" in step_schema["properties"]
        assert "action" in step_schema["properties"]
        assert "title" in step_schema["properties"]

    def test_schema_action_enum(self):
        """Test that action enum is correctly specified."""
        schema = build_plan_to_gemini_schema()

        action_schema = schema["properties"]["steps"]["items"]["properties"]["action"]
        assert "enum" in action_schema
        assert "create_file" in action_schema["enum"]
        assert "install_dependency" in action_schema["enum"]
        assert "create_component" in action_schema["enum"]

    def test_schema_project_type_enum(self):
        """Test that project_type enum is correctly specified."""
        schema = build_plan_to_gemini_schema()

        project_type_schema = schema["properties"]["project_type"]
        assert "enum" in project_type_schema
        assert "web" in project_type_schema["enum"]
        assert "react" in project_type_schema["enum"]
        assert "nextjs" in project_type_schema["enum"]


class TestActionType:
    """Tests for ActionType enum."""

    def test_action_types(self):
        """Test that all action types are available."""
        assert ActionType.CREATE_FILE == "create_file"
        assert ActionType.INSTALL_DEPENDENCY == "install_dependency"
        assert ActionType.CREATE_COMPONENT == "create_component"
        assert ActionType.SETUP_CONFIG == "setup_config"
        assert ActionType.ADD_ROUTE == "add_route"
        assert ActionType.ADD_API_ENDPOINT == "add_api_endpoint"
        assert ActionType.STYLE_COMPONENT == "style_component"
        assert ActionType.ADD_STATE_MANAGEMENT == "add_state_management"
        assert ActionType.INTEGRATE_API == "integrate_api"


class TestProjectType:
    """Tests for ProjectType enum."""

    def test_project_types(self):
        """Test that all project types are available."""
        assert ProjectType.WEB == "web"
        assert ProjectType.REACT == "react"
        assert ProjectType.NEXTJS == "nextjs"
        assert ProjectType.API == "api"
        assert ProjectType.MOBILE == "mobile"
        assert ProjectType.DESKTOP == "desktop"
        assert ProjectType.AGENT == "agent"


class TestDifficultyLevel:
    """Tests for DifficultyLevel enum."""

    def test_difficulty_levels(self):
        """Test that all difficulty levels are available."""
        assert DifficultyLevel.BEGINNER == "beginner"
        assert DifficultyLevel.INTERMEDIATE == "intermediate"
        assert DifficultyLevel.ADVANCED == "advanced"
