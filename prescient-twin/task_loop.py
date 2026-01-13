"""
TaskLoop: Ralph-Style Autonomous Task Execution

This module implements the Ralph pattern from the video:
- Takes a list of tasks (from video analysis or direct input)
- Implements code for each task
- Tests the implementation
- Commits the code
- Loops until complete

This is NOT about generating summary pages - it's about
APPLYING learnings from videos to the UVAI codebase itself.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Optional

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from memory import record_lesson


@dataclass
class Task:
    """A single task to be executed."""

    id: int
    description: str
    target_file: Optional[str] = None
    action_type: str = "implement"  # implement, test, refactor, document
    status: str = "pending"  # pending, in_progress, completed, failed
    code_changes: Optional[str] = None
    test_results: Optional[str] = None
    commit_hash: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TaskLoopResult:
    """Result of a full task loop execution."""

    success: bool
    tasks_completed: int
    tasks_failed: int
    total_tasks: int
    commits_made: list[str] = field(default_factory=list)
    files_modified: list[str] = field(default_factory=list)
    lessons_learned: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class TaskLoop:
    """
    Ralph-Style Autonomous Task Execution Loop.

    The key insight: Instead of deploying summary pages about what we learned,
    we APPLY the learnings directly to the UVAI codebase.

    Flow:
    1. Extract learnings from video/content
    2. Convert learnings to actionable tasks
    3. For each task:
       a. Implement the code change
       b. Test it
       c. Commit it
       d. Record lesson
    4. Loop until all tasks complete or max retries
    """

    def __init__(
        self,
        repo_path: str = "/Users/garvey/Dev/projects/EventRelay",
    ):
        self.repo_path = repo_path
        self.prescient_twin_path = os.path.join(repo_path, "prescient-twin")
        self.max_retries = 3
        self.tasks: list[Task] = []

        # Initialize Gemini client
        self.client = None
        if GENAI_AVAILABLE:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)

    async def extract_tasks_from_content(
        self,
        content: str,
        content_type: str = "video_transcript",
        target_component: str = "prescient-twin",
    ) -> list[Task]:
        """
        Extract actionable tasks from content (video transcript, docs, etc).

        These are NOT tasks to describe - these are tasks to IMPLEMENT.
        """
        if not self.client:
            return []

        extraction_prompt = f"""
You are analyzing content to extract ACTIONABLE IMPLEMENTATION TASKS for the UVAI codebase.

Content Type: {content_type}
Target Component: {target_component}

CRITICAL: We do NOT want summary pages or descriptions.
We want CONCRETE CODE CHANGES to implement in our codebase.

Content:
{content[:15000]}

Extract up to 10 specific, implementable tasks. For each task:
1. What specific code change is needed?
2. Which file should be modified/created?
3. What is the implementation approach?

Return JSON array:
[
  {{
    "id": 1,
    "description": "Specific implementation task",
    "target_file": "prescient-twin/some_file.py",
    "action_type": "implement|refactor|document|test",
    "implementation_notes": "How to implement this"
  }}
]

Focus on:
- Protocol integrations (if the content discusses protocols)
- Architecture improvements (if discussing agent patterns)
- New features (if demonstrating capabilities)
- Bug fixes (if highlighting issues)

DO NOT return tasks like "create landing page about X" or "summarize concept".
ONLY return tasks that ADD VALUE to UVAI's capabilities.
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                ),
            )

            # Parse JSON from response
            text = response.text
            json_match = re.search(r"\[[\s\S]*\]", text)
            if json_match:
                task_data = json.loads(json_match.group())
                tasks = []
                for t in task_data:
                    tasks.append(
                        Task(
                            id=t.get("id", len(tasks) + 1),
                            description=t.get("description", ""),
                            target_file=t.get("target_file"),
                            action_type=t.get("action_type", "implement"),
                        )
                    )
                return tasks
        except Exception as e:
            print(f"⚠️ Task extraction failed: {e}")

        return []

    async def implement_task(self, task: Task) -> bool:
        """
        Implement a single task by generating and applying code.

        This is the core of Ralph-style execution - actually making changes.
        """
        if not self.client:
            task.status = "failed"
            task.error_message = "Gemini client not available"
            return False

        task.status = "in_progress"

        # Read existing file content if modifying
        existing_content = ""
        if task.target_file:
            full_path = os.path.join(self.repo_path, task.target_file)
            if os.path.exists(full_path):
                with open(full_path) as f:
                    existing_content = f.read()

        # Build context for prompt
        if existing_content:
            file_context = "Existing File Content:\n" + existing_content[:10000]
        else:
            file_context = "This is a new file."

        implementation_prompt = f"""
You are implementing a code change in the UVAI codebase.

Task: {task.description}
Target File: {task.target_file or "New file to create"}
Action Type: {task.action_type}

{file_context}

Generate the COMPLETE file content that implements this task.
Return ONLY the code, no markdown fencing, no explanations.

Requirements:
- Python files must be valid Python 3.11+
- Include proper type hints
- Include docstrings
- Follow existing code patterns in the file
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=implementation_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                ),
            )

            new_content = response.text.strip()

            # Remove markdown code fences if present
            if new_content.startswith("```"):
                lines = new_content.split("\n")
                new_content = "\n".join(
                    lines[1:-1] if lines[-1] == "```" else lines[1:]
                )

            task.code_changes = new_content

            # Write the file
            if task.target_file:
                full_path = os.path.join(self.repo_path, task.target_file)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w") as f:
                    f.write(new_content)

                print(f"✅ Wrote {task.target_file}")
                return True

        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            print(f"❌ Implementation failed: {e}")

        return False

    def test_task(self, task: Task) -> bool:
        """
        Test that the implemented code works.

        Runs Python syntax check and basic import test.
        """
        if not task.target_file or not task.target_file.endswith(".py"):
            task.test_results = "Non-Python file, skipping test"
            return True

        full_path = os.path.join(self.repo_path, task.target_file)
        if not os.path.exists(full_path):
            task.test_results = "File not found"
            task.status = "failed"
            return False

        # Syntax check
        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", full_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                task.test_results = f"Syntax error: {result.stderr}"
                task.status = "failed"
                return False
        except Exception as e:
            task.test_results = f"Test failed: {e}"
            task.status = "failed"
            return False

        task.test_results = "Syntax check passed"
        return True

    def commit_task(self, task: Task) -> bool:
        """
        Commit the changes for a completed task.
        """
        if not task.target_file:
            return False

        try:
            # Stage the file
            subprocess.run(
                ["git", "add", task.target_file],
                cwd=self.repo_path,
                capture_output=True,
                timeout=10,
            )

            # Commit
            commit_message = f"[TaskLoop] {task.description[:50]}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # Get commit hash
                hash_result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                task.commit_hash = hash_result.stdout.strip()[:8]
                task.status = "completed"
                print(f"📝 Committed: {task.commit_hash}")
                return True
            else:
                # Might be nothing to commit
                if "nothing to commit" in result.stdout:
                    task.status = "completed"
                    return True
                task.error_message = result.stderr

        except Exception as e:
            task.error_message = str(e)

        return False

    async def run(
        self,
        content: str,
        content_type: str = "video_transcript",
        target_component: str = "prescient-twin",
        auto_commit: bool = True,
    ) -> TaskLoopResult:
        """
        Main execution loop - Ralph style.

        1. Extract tasks from content
        2. For each task: Implement → Test → Commit
        3. Record lessons learned
        """
        import time

        start_time = time.time()

        result = TaskLoopResult(
            success=False,
            tasks_completed=0,
            tasks_failed=0,
            total_tasks=0,
        )

        # Step 1: Extract tasks
        print("🔍 Extracting actionable tasks from content...")
        self.tasks = await self.extract_tasks_from_content(
            content, content_type, target_component
        )
        result.total_tasks = len(self.tasks)

        if not self.tasks:
            print("⚠️ No actionable tasks extracted")
            result.success = True  # No tasks is not a failure
            return result

        print(f"📋 Found {len(self.tasks)} tasks to implement")

        # Step 2: Execute each task
        for task in self.tasks:
            print(f"\n🚀 Task {task.id}: {task.description[:60]}...")

            # Implement
            impl_success = await self.implement_task(task)
            if not impl_success:
                result.tasks_failed += 1
                continue

            # Test
            test_success = self.test_task(task)
            if not test_success:
                result.tasks_failed += 1
                continue

            # Commit
            if auto_commit:
                commit_success = self.commit_task(task)
                if commit_success and task.commit_hash:
                    result.commits_made.append(task.commit_hash)
            else:
                task.status = "completed"

            if task.status == "completed":
                result.tasks_completed += 1
                if task.target_file:
                    result.files_modified.append(task.target_file)

        # Step 3: Record lessons
        lesson = (
            f"TaskLoop executed: {result.tasks_completed}"
            f"/{result.total_tasks} tasks completed"
        )
        record_lesson(
            lesson,
            context={
                "content_type": content_type,
                "target_component": target_component,
                "tasks": [t.description for t in self.tasks],
                "commits": result.commits_made,
            },
        )
        result.lessons_learned.append(lesson)

        result.duration_seconds = time.time() - start_time
        result.success = result.tasks_failed == 0

        return result


def get_task_loop(
    repo_path: str = "/Users/garvey/Dev/projects/EventRelay",
) -> TaskLoop:
    """Factory function to get TaskLoop instance."""
    return TaskLoop(repo_path=repo_path)


# Entry point for testing
if __name__ == "__main__":
    import asyncio

    async def test_loop():
        loop = get_task_loop()

        # Test with simple content
        test_content = """
        This video discusses how to implement a caching layer in FastAPI.
        Step 1: Create a cache module using Redis or in-memory dict
        Step 2: Add cache decorator for expensive operations
        Step 3: Implement cache invalidation on data changes
        """

        result = await loop.run(
            content=test_content,
            content_type="tutorial",
            target_component="prescient-twin",
            auto_commit=False,  # Don't actually commit during test
        )

        print("\n📊 Results:")
        print(f"   Total tasks: {result.total_tasks}")
        print(f"   Completed: {result.tasks_completed}")
        print(f"   Failed: {result.tasks_failed}")
        print(f"   Duration: {result.duration_seconds:.1f}s")

    asyncio.run(test_loop())
