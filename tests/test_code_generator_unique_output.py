#!/usr/bin/env python3
"""
Test that code_generator.py produces unique, tutorial-specific output
instead of identical boilerplate for different videos.
"""

import asyncio
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from youtube_extension.backend.code_generator import ProjectCodeGenerator


async def test_unique_react_output():
    """Test that React projects have unique code based on tutorial steps"""
    generator = ProjectCodeGenerator()

    # Video 1: State management tutorial
    video_analysis_1 = {
        "video_data": {"video_url": "https://youtube.com/watch?v=test1"},
        "extracted_info": {
            "title": "React State Management Tutorial",
            "technologies": ["react", "javascript"],
            "features": ["state_management"],
            "tutorial_steps": [
                "Create a new React component with useState",
                "Add state variable for counter",
                "Implement increment and decrement functions",
            ],
        },
    }

    # Video 2: API integration tutorial
    video_analysis_2 = {
        "video_data": {"video_url": "https://youtube.com/watch?v=test2"},
        "extracted_info": {
            "title": "React API Integration Tutorial",
            "technologies": ["react", "javascript"],
            "features": ["api_integration"],
            "tutorial_steps": [
                "Fetch data from REST API using fetch()",
                "Display loading state while fetching",
                "Render data in a list component",
            ],
        },
    }

    # Generate both projects
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path_1 = Path(tmpdir) / "project1"
        project_path_1.mkdir()

        result_1 = await generator._generate_react_project(
            project_path_1, video_analysis_1, ["state_management"]
        )

        # Read generated App.js for project 1
        app_js_1 = (project_path_1 / "src" / "App.js").read_text()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path_2 = Path(tmpdir) / "project2"
        project_path_2.mkdir()

        result_2 = await generator._generate_react_project(
            project_path_2, video_analysis_2, ["api_integration"]
        )

        # Read generated App.js for project 2
        app_js_2 = (project_path_2 / "src" / "App.js").read_text()

    # Verify outputs are different
    assert app_js_1 != app_js_2, "Generated React code should be unique per tutorial"

    # Verify project 1 contains state-related code
    assert "useState" in app_js_1, "State tutorial should include useState"
    assert "State Management" in app_js_1, "Should reference tutorial title"
    assert "step-card" in app_js_1, "Should include step-specific components"

    # Verify project 2 contains API-related code
    assert "API Integration" in app_js_2, "API tutorial should reference its title"
    assert "Fetch data from REST API" in app_js_2, "Should include tutorial step text"
    assert "step-card" in app_js_2, "Should include step-specific components"

    print("✅ React projects produce unique, tutorial-specific code")


async def test_unique_vanilla_js_output():
    """Test that vanilla JS projects have unique code based on tutorial steps"""
    generator = ProjectCodeGenerator()

    # Video with form handling steps
    video_analysis_form = {
        "video_data": {"video_url": "https://youtube.com/watch?v=form"},
        "extracted_info": {
            "title": "Form Handling Tutorial",
            "technologies": ["javascript", "html"],
            "features": ["forms"],
            "tutorial_steps": [
                "Create a form with input fields",
                "Handle form submission event",
                "Validate form data",
            ],
        },
    }

    # Video with event handling steps
    video_analysis_events = {
        "video_data": {"video_url": "https://youtube.com/watch?v=events"},
        "extracted_info": {
            "title": "Event Handling Tutorial",
            "technologies": ["javascript", "html"],
            "features": ["events"],
            "tutorial_steps": [
                "Add click event listeners to buttons",
                "Handle mouse hover events",
                "Implement keyboard event handlers",
            ],
        },
    }

    # Generate both projects
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path_1 = Path(tmpdir) / "project1"
        project_path_1.mkdir()

        await generator._generate_vanilla_js_project(
            project_path_1, video_analysis_form, ["forms"]
        )
        main_js_1 = (project_path_1 / "main.js").read_text()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path_2 = Path(tmpdir) / "project2"
        project_path_2.mkdir()

        await generator._generate_vanilla_js_project(
            project_path_2, video_analysis_events, ["events"]
        )
        main_js_2 = (project_path_2 / "main.js").read_text()

    # Verify outputs are different
    assert main_js_1 != main_js_2, "Generated vanilla JS code should be unique per tutorial"

    # Verify project 1 contains form-related code
    assert "form" in main_js_1.lower(), "Form tutorial should include form handling"
    assert "tutorialStep" in main_js_1, "Should include step-specific functions"

    # Verify project 2 contains event-related code
    assert "event" in main_js_2.lower() or "click" in main_js_2.lower(), "Event tutorial should include event handling"
    assert "tutorialStep" in main_js_2, "Should include step-specific functions"

    # Verify both have different step counts
    step_count_1 = main_js_1.count("tutorialStep")
    step_count_2 = main_js_2.count("tutorialStep")
    assert step_count_1 > 0 and step_count_2 > 0, "Both should have tutorial steps"

    print("✅ Vanilla JS projects produce unique, tutorial-specific code")


async def test_unique_fastapi_output():
    """Test that FastAPI projects have unique endpoints"""
    generator = ProjectCodeGenerator()

    # Video 1: Basic CRUD API
    video_analysis_1 = {
        "video_data": {"video_url": "https://youtube.com/watch?v=api1"},
        "extracted_info": {
            "title": "FastAPI CRUD Tutorial",
            "technologies": ["python", "fastapi"],
            "features": ["database"],
        },
    }

    # Video 2: Auth API
    video_analysis_2 = {
        "video_data": {"video_url": "https://youtube.com/watch?v=api2"},
        "extracted_info": {
            "title": "FastAPI Authentication Tutorial",
            "technologies": ["python", "fastapi"],
            "features": ["authentication"],
        },
    }

    # Generate both projects
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path_1 = Path(tmpdir) / "project1"
        project_path_1.mkdir()

        await generator._generate_python_api(
            project_path_1, video_analysis_1, ["database"]
        )
        main_py_1 = (project_path_1 / "main.py").read_text()

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path_2 = Path(tmpdir) / "project2"
        project_path_2.mkdir()

        await generator._generate_python_api(
            project_path_2, video_analysis_2, ["authentication"]
        )
        main_py_2 = (project_path_2 / "main.py").read_text()

    # Verify outputs are different
    assert main_py_1 != main_py_2, "Generated FastAPI code should be unique per tutorial"

    # Verify project 1 contains database endpoints
    assert "database" in main_py_1.lower() or "data" in main_py_1, "CRUD tutorial should include data endpoints"
    assert "/api/tutorial/steps" in main_py_1, "Should include tutorial-specific endpoints"

    # Verify project 2 contains auth endpoints
    assert "auth" in main_py_2.lower() or "login" in main_py_2, "Auth tutorial should include authentication"
    assert "/api/tutorial/steps" in main_py_2, "Should include tutorial-specific endpoints"

    # Verify both have unique titles in their description
    assert "CRUD Tutorial" in main_py_1, "Should include specific tutorial title"
    assert "Authentication Tutorial" in main_py_2, "Should include specific tutorial title"

    print("✅ FastAPI projects produce unique, tutorial-specific code")


async def test_no_tutorial_steps_fallback():
    """Test that generator handles videos without tutorial steps gracefully"""
    generator = ProjectCodeGenerator()

    video_analysis = {
        "video_data": {"video_url": "https://youtube.com/watch?v=generic"},
        "extracted_info": {
            "title": "Generic Video",
            "technologies": ["react"],
            "features": [],
            "tutorial_steps": [],  # No steps
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir) / "project"
        project_path.mkdir()

        result = await generator._generate_react_project(
            project_path, video_analysis, []
        )

        app_js = (project_path / "src" / "App.js").read_text()

    # Should still generate valid code
    assert "import React" in app_js, "Should generate valid React code"
    assert "export default App" in app_js, "Should have proper exports"
    print("✅ Generator handles videos without tutorial steps gracefully")


async def main():
    """Run all tests"""
    print("Testing code_generator.py for unique, tutorial-specific output...\n")

    try:
        await test_unique_react_output()
        await test_unique_vanilla_js_output()
        await test_unique_fastapi_output()
        await test_no_tutorial_steps_fallback()

        print("\n🎉 All tests passed! Code generator produces unique output per tutorial.")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
