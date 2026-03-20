"""
BuildPlan Model - Structured Output for Stage 2: Semantic Logic Parsing
========================================================================

This module defines the structured output schema for video analysis that transforms
raw transcripts and visual cues into actionable, deterministic build instructions.

The BuildPlan is the primary artifact that flows from Stage 2 (Semantic Logic Parsing)
to Stage 3 (Code Generation), eliminating the need for loose text and template fallbacks.
"""

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of build actions that can be performed."""

    CREATE_FILE = "create_file"
    INSTALL_DEPENDENCY = "install_dependency"
    CREATE_COMPONENT = "create_component"
    SETUP_CONFIG = "setup_config"
    ADD_ROUTE = "add_route"
    ADD_API_ENDPOINT = "add_api_endpoint"
    STYLE_COMPONENT = "style_component"
    ADD_STATE_MANAGEMENT = "add_state_management"
    INTEGRATE_API = "integrate_api"


class BuildStep(BaseModel):
    """A single step in the build plan with all necessary metadata."""

    step_number: int = Field(
        ...,
        description="Sequential step number (1-indexed)",
        ge=1
    )

    action: ActionType = Field(
        ...,
        description="Type of action to perform in this step"
    )

    title: str = Field(
        ...,
        description="Short, descriptive title for this step",
        max_length=100
    )

    description: str = Field(
        ...,
        description="Detailed description of what this step accomplishes",
        max_length=500
    )

    target_file: Optional[str] = Field(
        None,
        description="Target file path for this action (e.g., 'src/App.jsx')"
    )

    code_snippet: Optional[str] = Field(
        None,
        description="Code content to be added or modified"
    )

    command: Optional[str] = Field(
        None,
        description="CLI command to execute (e.g., 'npm install react')"
    )

    dependencies: list[int] = Field(
        default_factory=list,
        description="List of step numbers that must complete before this step"
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context or configuration for this step"
    )


class ProjectType(str, Enum):
    """Type of project being generated."""

    WEB = "web"
    REACT = "react"
    NEXTJS = "nextjs"
    API = "api"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    AGENT = "agent"


class DifficultyLevel(str, Enum):
    """Complexity level of the project."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class BuildPlan(BaseModel):
    """
    Structured build plan extracted from video analysis.

    This is the primary output of Stage 2 (Semantic Logic Parsing) and the
    primary input to Stage 3 (Code Generation).
    """

    title: str = Field(
        ...,
        description="Project title derived from video content",
        max_length=200
    )

    description: str = Field(
        ...,
        description="Brief project description",
        max_length=1000
    )

    project_type: ProjectType = Field(
        ...,
        description="Type of project to generate"
    )

    difficulty_level: DifficultyLevel = Field(
        DifficultyLevel.BEGINNER,
        description="Complexity level of the project"
    )

    technologies: list[str] = Field(
        ...,
        description="Primary technologies and frameworks used",
        min_items=1
    )

    features: list[str] = Field(
        default_factory=list,
        description="Key features to implement"
    )

    steps: list[BuildStep] = Field(
        ...,
        description="Ordered list of build steps with dependencies",
        min_items=1
    )

    estimated_duration: Optional[str] = Field(
        None,
        description="Estimated time to complete (e.g., '30 minutes')"
    )

    prerequisites: list[str] = Field(
        default_factory=list,
        description="Required knowledge or setup before starting"
    )

    learning_objectives: list[str] = Field(
        default_factory=list,
        description="What the user will learn by completing this project"
    )

    video_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Source video information (video_id, timestamps, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Todo App with React and Tailwind CSS",
                "description": "Build a responsive todo application using React and Tailwind CSS with local storage persistence",
                "project_type": "react",
                "difficulty_level": "beginner",
                "technologies": ["react", "tailwindcss", "javascript"],
                "features": ["responsive_design", "local_storage", "crud_operations"],
                "steps": [
                    {
                        "step_number": 1,
                        "action": "create_file",
                        "title": "Create React App",
                        "description": "Initialize a new React application using create-react-app",
                        "command": "npx create-react-app todo-app",
                        "dependencies": [],
                        "metadata": {"framework": "react"}
                    },
                    {
                        "step_number": 2,
                        "action": "install_dependency",
                        "title": "Install Tailwind CSS",
                        "description": "Add Tailwind CSS for styling",
                        "command": "npm install -D tailwindcss postcss autoprefixer",
                        "dependencies": [1],
                        "metadata": {"styling": "tailwindcss"}
                    },
                    {
                        "step_number": 3,
                        "action": "create_component",
                        "title": "Create TodoList Component",
                        "description": "Create the main TodoList component with state management",
                        "target_file": "src/components/TodoList.jsx",
                        "code_snippet": "import { useState } from 'react';\n\nfunction TodoList() {\n  const [todos, setTodos] = useState([]);\n  return <div>...</div>;\n}",
                        "dependencies": [2],
                        "metadata": {"component_type": "functional"}
                    }
                ],
                "estimated_duration": "1 hour",
                "prerequisites": ["Node.js installed", "Basic JavaScript knowledge"],
                "learning_objectives": [
                    "Learn React hooks (useState, useEffect)",
                    "Understand component composition",
                    "Practice Tailwind CSS utility classes"
                ],
                "video_metadata": {
                    "video_id": "example123",
                    "source_url": "https://youtube.com/watch?v=example123"
                }
            }
        }


def build_plan_to_gemini_schema() -> dict[str, Any]:
    """
    Convert BuildPlan Pydantic model to Gemini-compatible JSON schema.

    This schema can be passed to Gemini's response_schema parameter
    to enforce structured output.
    """
    return {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Project title derived from video content"
            },
            "description": {
                "type": "string",
                "description": "Brief project description"
            },
            "project_type": {
                "type": "string",
                "enum": ["web", "react", "nextjs", "api", "mobile", "desktop", "agent"],
                "description": "Type of project to generate"
            },
            "difficulty_level": {
                "type": "string",
                "enum": ["beginner", "intermediate", "advanced"],
                "description": "Complexity level of the project"
            },
            "technologies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Primary technologies and frameworks used"
            },
            "features": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key features to implement"
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "step_number": {
                            "type": "integer",
                            "description": "Sequential step number (1-indexed)"
                        },
                        "action": {
                            "type": "string",
                            "enum": [
                                "create_file",
                                "install_dependency",
                                "create_component",
                                "setup_config",
                                "add_route",
                                "add_api_endpoint",
                                "style_component",
                                "add_state_management",
                                "integrate_api"
                            ],
                            "description": "Type of action to perform"
                        },
                        "title": {
                            "type": "string",
                            "description": "Short, descriptive title for this step"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of what this step accomplishes"
                        },
                        "target_file": {
                            "type": "string",
                            "description": "Target file path for this action"
                        },
                        "code_snippet": {
                            "type": "string",
                            "description": "Code content to be added or modified"
                        },
                        "command": {
                            "type": "string",
                            "description": "CLI command to execute"
                        },
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of step numbers that must complete before this step"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Additional context or configuration"
                        }
                    },
                    "required": ["step_number", "action", "title", "description"]
                },
                "description": "Ordered list of build steps with dependencies"
            },
            "estimated_duration": {
                "type": "string",
                "description": "Estimated time to complete"
            },
            "prerequisites": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Required knowledge or setup before starting"
            },
            "learning_objectives": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What the user will learn by completing this project"
            },
            "video_metadata": {
                "type": "object",
                "description": "Source video information"
            }
        },
        "required": ["title", "description", "project_type", "technologies", "steps"]
    }
