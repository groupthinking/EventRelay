"""Unit tests for the AST validation layer in CodeGeneratorAgent."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from agents.specialized.code_generator import CodeGeneratorAgent

# ===========================================================================
# CodeGeneratorAgent.validate_python_syntax
# ===========================================================================


class TestValidatePythonSyntax:
    def test_valid_code_returns_valid_true(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("x = 1 + 2\n")
        assert result["valid"] is True

    def test_valid_code_has_empty_errors(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("def foo():\n    pass\n")
        assert result["errors"] == []

    def test_invalid_code_returns_valid_false(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("def foo(:\n    pass\n")
        assert result["valid"] is False

    def test_invalid_code_has_errors(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("def foo(:\n    pass\n")
        assert len(result["errors"]) > 0

    def test_error_dict_has_message_key(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("???")
        assert "message" in result["errors"][0]

    def test_error_dict_has_line_key(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("???")
        assert "line" in result["errors"][0]

    def test_error_dict_has_offset_key(self) -> None:
        result = CodeGeneratorAgent.validate_python_syntax("???")
        assert "offset" in result["errors"][0]

    def test_empty_string_is_valid(self) -> None:
        # Empty module is syntactically valid Python
        result = CodeGeneratorAgent.validate_python_syntax("")
        assert result["valid"] is True

    def test_multiline_valid_code(self) -> None:
        code = (
            "from typing import Optional\n\n"
            "class Foo:\n"
            "    def bar(self, x: Optional[int] = None) -> str:\n"
            "        return str(x)\n"
        )
        result = CodeGeneratorAgent.validate_python_syntax(code)
        assert result["valid"] is True

    def test_indentation_error_detected(self) -> None:
        code = "if True:\npass\n"
        result = CodeGeneratorAgent.validate_python_syntax(code)
        assert result["valid"] is False


# ===========================================================================
# CodeGeneratorAgent.execute — AST validation fields in return value
# ===========================================================================


class TestExecuteReturnsValidationFields:
    def test_execute_returns_syntax_valid_field(self) -> None:
        agent = CodeGeneratorAgent()
        result = asyncio.run(agent.execute({"intent": "api endpoint", "context": {}}))
        assert "syntax_valid" in result

    def test_execute_returns_syntax_errors_field(self) -> None:
        agent = CodeGeneratorAgent()
        result = asyncio.run(agent.execute({"intent": "crud", "context": {}}))
        assert "syntax_errors" in result

    def test_execute_syntax_valid_is_bool(self) -> None:
        agent = CodeGeneratorAgent()
        result = asyncio.run(agent.execute({"intent": "data model", "context": {}}))
        assert isinstance(result["syntax_valid"], bool)

    def test_execute_syntax_errors_is_list(self) -> None:
        agent = CodeGeneratorAgent()
        result = asyncio.run(agent.execute({"intent": "generic", "context": {}}))
        assert isinstance(result["syntax_errors"], list)

    def test_template_generated_code_is_syntactically_valid(self) -> None:
        """Template-generated Python code must pass AST validation."""
        agent = CodeGeneratorAgent()
        for intent in ("api endpoint", "crud", "data model", "generic"):
            result = asyncio.run(agent.execute({"intent": intent, "context": {}}))
            assert result["syntax_valid"] is True, (
                f"Intent '{intent}' produced invalid Python: {result['syntax_errors']}"
            )

    def test_execute_still_returns_generated_code(self) -> None:
        agent = CodeGeneratorAgent()
        result = asyncio.run(agent.execute({"intent": "api endpoint", "context": {}}))
        assert "generated_code" in result
        assert len(result["generated_code"]) > 0

    def test_execute_still_returns_success_flag(self) -> None:
        agent = CodeGeneratorAgent()
        result = asyncio.run(agent.execute({"intent": "api endpoint", "context": {}}))
        assert result["success"] is True
