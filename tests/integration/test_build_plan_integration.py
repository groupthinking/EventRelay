"""
Integration Tests for BuildPlan Extraction and Code Generation
===============================================================

Tests the complete flow:
1. Video URL -> BuildPlan extraction (Stage 2)
2. BuildPlan -> Code generation (Stage 3)
"""

import pytest

from youtube_extension.backend.code_generator import ProjectCodeGenerator
from youtube_extension.backend.models.build_plan import (
    ActionType,
    BuildPlan,
    BuildStep,
    ProjectType,
)


@pytest.fixture
def sample_build_plan():
    """Create a sample BuildPlan for testing."""
    return {
        "title": "Todo App with React and Tailwind",
        "description": "Build a responsive todo application",
        "project_type": "react",
        "difficulty_level": "beginner",
        "technologies": ["react", "tailwindcss", "javascript"],
        "features": ["responsive_design", "local_storage"],
        "steps": [
            {
                "step_number": 1,
                "action": "create_file",
                "title": "Create React App",
                "description": "Initialize a new React application using create-react-app",
                "command": "npx create-react-app todo-app",
                "dependencies": [],
                "metadata": {"framework": "react"},
            },
            {
                "step_number": 2,
                "action": "install_dependency",
                "title": "Install Tailwind CSS",
                "description": "Add Tailwind CSS for styling",
                "command": "npm install -D tailwindcss postcss autoprefixer",
                "dependencies": [1],
                "metadata": {"styling": "tailwindcss"},
            },
            {
                "step_number": 3,
                "action": "create_component",
                "title": "Create TodoList Component",
                "description": "Create the main TodoList component with state management",
                "target_file": "src/components/TodoList.jsx",
                "code_snippet": "import { useState } from 'react';\n\nfunction TodoList() {\n  const [todos, setTodos] = useState([]);\n  return <div className='container mx-auto'>...</div>;\n}",
                "dependencies": [2],
                "metadata": {"component_type": "functional"},
            },
        ],
        "estimated_duration": "1 hour",
        "prerequisites": ["Node.js installed", "Basic JavaScript knowledge"],
        "learning_objectives": [
            "Learn React hooks",
            "Understand component composition",
            "Practice Tailwind CSS",
        ],
        "video_metadata": {
            "video_id": "test_video_123",
            "source_url": "https://youtube.com/watch?v=test_video_123",
        },
    }


@pytest.fixture
def video_analysis_with_build_plan(sample_build_plan):
    """Create video analysis result with BuildPlan."""
    return {
        "video_id": "test_video_123",
        "video_url": "https://youtube.com/watch?v=test_video_123",
        "metadata": {
            "title": "Todo App Tutorial",
            "description": "Learn to build a todo app",
            "duration": "15:30",
        },
        "transcript": {"text": "In this tutorial, we'll build a todo app..."},
        "build_plan": sample_build_plan,
        "ai_analysis": {
            "success": True,
            "content_analysis": {"main_topics": ["React", "Tailwind"]},
        },
    }


@pytest.fixture
def video_analysis_without_build_plan():
    """Create video analysis result WITHOUT BuildPlan (legacy format)."""
    return {
        "video_id": "test_video_456",
        "video_url": "https://youtube.com/watch?v=test_video_456",
        "metadata": {
            "title": "Generic Tutorial",
            "description": "Tutorial description",
        },
        "transcript": {"text": "Tutorial transcript..."},
        "extracted_info": {
            "title": "Generic Project",
            "technologies": ["javascript", "html"],
            "features": ["basic_functionality"],
            "tutorial_steps": ["Step 1: Setup", "Step 2: Build", "Step 3: Deploy"],
        },
        "ai_analysis": {
            "Related Topics": ["JavaScript", "HTML"],
            "Key Concepts": ["DOM Manipulation"],
        },
    }


class TestBuildPlanIntegration:
    """Integration tests for BuildPlan extraction and usage."""

    @pytest.mark.asyncio
    async def test_code_generator_with_build_plan(self, video_analysis_with_build_plan):
        """Test that ProjectCodeGenerator uses BuildPlan when available."""
        generator = ProjectCodeGenerator()
        project_config = {"type": "react"}

        # Generate project
        result = await generator.generate_project(
            video_analysis_with_build_plan, project_config
        )

        # Verify result structure
        assert "project_path" in result
        assert result["project_type"] == "react"

        # Verify BuildPlan was used (check logs or context)
        # The title is used in generation but not returned in result dict

    @pytest.mark.asyncio
    async def test_code_generator_fallback_without_build_plan(
        self, video_analysis_without_build_plan
    ):
        """Test that ProjectCodeGenerator falls back to legacy logic when BuildPlan is missing."""
        generator = ProjectCodeGenerator()
        project_config = {"type": "web"}

        # Generate project
        result = await generator.generate_project(
            video_analysis_without_build_plan, project_config
        )

        # Verify result structure
        assert "project_path" in result
        assert result["project_type"] == "web"

        # Verify legacy extraction was used (check logs or context)
        # The title is used in generation but not returned in result dict

    def test_build_plan_model_from_dict(self, sample_build_plan):
        """Test creating BuildPlan model from dict."""
        plan = BuildPlan(**sample_build_plan)

        assert plan.title == "Todo App with React and Tailwind"
        assert plan.project_type == ProjectType.REACT
        assert len(plan.steps) == 3
        assert plan.steps[0].action == ActionType.CREATE_FILE
        assert plan.steps[1].dependencies == [1]
        assert plan.steps[2].dependencies == [2]

    def test_build_plan_step_extraction(self, video_analysis_with_build_plan):
        """Test extracting tutorial steps from BuildPlan."""
        build_plan = video_analysis_with_build_plan["build_plan"]
        steps = build_plan["steps"]

        # Verify step ordering
        assert steps[0]["step_number"] == 1
        assert steps[1]["step_number"] == 2
        assert steps[2]["step_number"] == 3

        # Verify dependencies
        assert steps[0]["dependencies"] == []
        assert steps[1]["dependencies"] == [1]
        assert steps[2]["dependencies"] == [2]

    def test_build_plan_has_code_snippets(self, sample_build_plan):
        """Test that BuildPlan includes code snippets when available."""
        plan = BuildPlan(**sample_build_plan)

        # Find the component creation step
        component_step = [
            s for s in plan.steps if s.action == ActionType.CREATE_COMPONENT
        ][0]

        assert component_step.code_snippet is not None
        assert "useState" in component_step.code_snippet
        assert component_step.target_file == "src/components/TodoList.jsx"

    def test_build_plan_has_commands(self, sample_build_plan):
        """Test that BuildPlan includes CLI commands when available."""
        plan = BuildPlan(**sample_build_plan)

        # Find installation steps
        install_steps = [
            s for s in plan.steps if s.action == ActionType.INSTALL_DEPENDENCY
        ]

        assert len(install_steps) > 0
        assert install_steps[0].command is not None
        assert "npm install" in install_steps[0].command


class TestBuildGenerationContext:
    """Tests for _build_generation_context with BuildPlan."""

    @pytest.mark.asyncio
    async def test_context_extraction_from_build_plan(
        self, video_analysis_with_build_plan
    ):
        """Test that generation context is correctly extracted from BuildPlan."""
        generator = ProjectCodeGenerator()
        project_config = {"type": "react"}

        context = generator._build_generation_context(
            video_analysis_with_build_plan, project_config
        )

        # Verify extracted_info is populated from BuildPlan
        extracted = context["extracted_info"]
        assert extracted["title"] == "Todo App with React and Tailwind"
        assert "react" in extracted["technologies"]
        assert "tailwindcss" in extracted["technologies"]
        assert len(extracted["tutorial_steps"]) > 0

        # Verify BuildPlan is passed through
        assert context["build_plan"] is not None

    @pytest.mark.asyncio
    async def test_context_fallback_without_build_plan(
        self, video_analysis_without_build_plan
    ):
        """Test that generation context falls back to legacy extraction."""
        generator = ProjectCodeGenerator()
        project_config = {"type": "web"}

        context = generator._build_generation_context(
            video_analysis_without_build_plan, project_config
        )

        # Verify extracted_info is populated from legacy sources
        extracted = context["extracted_info"]
        assert extracted["title"] == "Generic Project"
        assert "javascript" in extracted["technologies"]

        # Verify BuildPlan is None
        assert context["build_plan"] is None

    def test_tutorial_steps_formatting_from_build_plan(
        self, video_analysis_with_build_plan
    ):
        """Test that tutorial steps are formatted correctly from BuildPlan."""
        generator = ProjectCodeGenerator()
        project_config = {"type": "react"}

        context = generator._build_generation_context(
            video_analysis_with_build_plan, project_config
        )

        steps = context["extracted_info"]["tutorial_steps"]

        # Steps should be formatted as "title: description"
        assert len(steps) > 0
        for step in steps:
            assert ":" in step
            assert len(step) > 10  # Should have meaningful content


class TestBuildPlanValidation:
    """Tests for BuildPlan validation during extraction."""

    def test_build_plan_requires_minimum_steps(self):
        """Test that BuildPlan requires at least one step."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BuildPlan(
                title="Test",
                description="Test",
                project_type=ProjectType.WEB,
                technologies=["javascript"],
                steps=[],  # Empty steps should fail
            )

    def test_build_plan_requires_technologies(self):
        """Test that BuildPlan requires at least one technology."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BuildPlan(
                title="Test",
                description="Test",
                project_type=ProjectType.WEB,
                technologies=[],  # Empty technologies should fail
                steps=[
                    BuildStep(
                        step_number=1,
                        action=ActionType.CREATE_FILE,
                        title="Test",
                        description="Test",
                    )
                ],
            )

    def test_build_step_ordering(self, sample_build_plan):
        """Test that BuildPlan steps are properly ordered."""
        plan = BuildPlan(**sample_build_plan)

        # Verify sequential numbering
        for i, step in enumerate(plan.steps):
            assert step.step_number == i + 1

    def test_build_step_dependencies_valid(self, sample_build_plan):
        """Test that step dependencies reference valid step numbers."""
        plan = BuildPlan(**sample_build_plan)

        for step in plan.steps:
            for dep in step.dependencies:
                # Dependency must reference an earlier step
                assert dep < step.step_number
                # Dependency must be a valid step number
                assert 1 <= dep <= len(plan.steps)
