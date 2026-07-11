import sys
from pathlib import Path
from unittest.mock import MagicMock

# Mocking modules that might be missing in the environment
sys.modules['aiohttp'] = MagicMock()
sys.modules['google.genai'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

from src.agents.specialized.quality_agent import QualityAgent

def test_check_line_quality_task_markers():
    agent = QualityAgent()
    agent.project_path = Path("/mock/project")
    file_path = Path("/mock/project/test_file.py")

    lines = [
        "def main():",
        "    # TODO: implement this",
        "    # FIXME: fix this bug",
        "    # HACK: temporary fix",
        "    # XXX: important note",
        "    # Just a normal comment",
        "    print('hello')"
    ]

    issues = agent.check_line_quality(lines, file_path)

    # Filter for todo_comment issues (using the concatenated name)
    todo_issues = [i for i in issues if i.issue_type == "todo_comment"]

    assert len(todo_issues) == 4

    descriptions = [i.description for i in todo_issues]
    assert any("Line 2" in d for d in descriptions)
    assert any("Line 3" in d for d in descriptions)
    assert any("Line 4" in d for d in descriptions)
    assert any("Line 5" in d for d in descriptions)

    for issue in todo_issues:
        assert issue.severity == "low"
        assert "task marker" in issue.description.lower()

if __name__ == "__main__":
    test_check_line_quality_task_markers()
    print("Test passed!")
