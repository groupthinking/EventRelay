"""
SafeSandboxTool - E2B Remote Code Execution

The agent writes code here, not on your hard drive.
Requires E2B_API_KEY environment variable.
"""

import os
from typing import Any

try:
    from smolagents import Tool
except ImportError:
    # Fallback for type hints
    class Tool:
        name: str = ""
        description: str = ""
        inputs: dict = {}
        output_type: str = ""

        def forward(self, **kwargs) -> Any: ...


class SafeSandboxTool(Tool):
    """
    Executes Python code in a secure remote sandbox (E2B).
    The agent can build and test tools here without affecting local filesystem.
    """

    name = "sandbox_executor"
    description = """
    Executes Python code in a secure remote sandbox.
    Use this to test new tools, run risky calculations, or prototype code.
    The sandbox is completely isolated - nothing you do here affects the local machine.
    """
    inputs = {
        "code": {
            "type": "string",
            "description": "Python code to execute in the sandbox.",
        }
    }
    output_type = "string"

    def __init__(self):
        super().__init__()
        self._sandbox_available = self._check_e2b_available()

    def _check_e2b_available(self) -> bool:
        """Check if E2B is configured"""
        if "E2B_API_KEY" not in os.environ:
            print("⚠️  E2B_API_KEY not set - sandbox will use mock mode")
            return False
        try:
            from e2b_code_interpreter import Sandbox

            return True
        except ImportError:
            print("⚠️  e2b_code_interpreter not installed")
            return False

    def forward(self, code: str) -> str:
        """Execute code in sandbox"""
        if not self._sandbox_available:
            return self._mock_execute(code)

        return self._real_execute(code)

    def _real_execute(self, code: str) -> str:
        """Execute in real E2B sandbox"""
        from e2b_code_interpreter import Sandbox

        try:
            with Sandbox() as sandbox:
                execution = sandbox.run_code(code)

                if execution.error:
                    return f"🔴 RUNTIME ERROR:\n{execution.error}"

                output_parts = []
                if execution.logs.stdout:
                    output_parts.append(f"📤 STDOUT:\n{execution.logs.stdout}")
                if execution.logs.stderr:
                    output_parts.append(f"⚠️  STDERR:\n{execution.logs.stderr}")
                if execution.results:
                    for result in execution.results:
                        if hasattr(result, "text"):
                            output_parts.append(f"📊 RESULT:\n{result.text}")

                if not output_parts:
                    return "✅ Code executed successfully (no output)"

                return "\n\n".join(output_parts)

        except Exception as e:
            return f"🔴 SANDBOX ERROR: {str(e)}"

    def _mock_execute(self, code: str) -> str:
        """Mock execution for testing without E2B"""
        # Simple mock that just validates syntax
        try:
            compile(code, "<sandbox>", "exec")
            return f"✅ [MOCK MODE] Code syntax validated:\n```python\n{code[:200]}{'...' if len(code) > 200 else ''}\n```"
        except SyntaxError as e:
            return f"🔴 [MOCK MODE] Syntax Error: {e}"


# Quick test
if __name__ == "__main__":
    tool = SafeSandboxTool()
    result = tool.forward("print('Hello from the sandbox!')")
    print(result)
