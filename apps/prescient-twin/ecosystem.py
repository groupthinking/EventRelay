"""
Prescient Twin - Ecosystem Entry Point

The main ecosystem file that ties everything together.
This is the "Brain" that coordinates:
- SafeSandboxTool (The Hands)
- HybridRouter (The Multi-Brain)
- ToolRepository (The Memory)
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from router import HybridRouter
from memory import load_evolved_tools, save_new_tool, record_lesson, get_tool_stats
from sandbox_tool import SafeSandboxTool


class PrescientTwin:
    """
    The main orchestrator - coordinates all components of the self-evolving system.
    """

    def __init__(self, enable_full_agents: bool = False):
        """
        Initialize the Prescient Twin ecosystem.

        Args:
            enable_full_agents: If True, initialize full CodeAgents (slower startup).
                              If False, use lightweight mode for faster startup.
        """
        print("🌟 Initializing Prescient Twin Ecosystem...")

        # Initialize components
        self.sandbox = SafeSandboxTool()
        self.router = HybridRouter(enable_agents=enable_full_agents)
        self.evolved_tools = load_evolved_tools()

        print(f"📊 Loaded {len(self.evolved_tools)} evolved tools from memory")
        print("✅ Prescient Twin Ready\n")

    def evolve(self, task: str, learn: bool = True) -> str:
        """
        Execute a task through the hybrid router.

        Args:
            task: The task description
            learn: If True, record the task and result as a lesson

        Returns:
            The result string
        """
        result = self.router.route(task)

        if learn and result["success"]:
            record_lesson(
                f"Completed task with {result['brain']}: {task[:50]}...",
                {"brain": result["brain"], "task": task},
            )

        return result["result"]

    def sandbox_execute(self, code: str) -> str:
        """Execute code in the safe sandbox"""
        return self.sandbox.forward(code)

    def create_tool(self, code: str, name: str, description: str = "") -> str:
        """
        Create and persist a new evolved tool.

        Args:
            code: Python source code for the tool
            name: Name for the tool
            description: What the tool does

        Returns:
            Path to the saved tool file
        """
        # First, validate in sandbox
        validation = self.sandbox_execute(f"compile({repr(code)}, '<tool>', 'exec')")

        if "Error" in validation:
            return f"❌ Tool validation failed: {validation}"

        # Save the tool
        filepath = save_new_tool(code, name, description)

        # Reload tools
        self.evolved_tools = load_evolved_tools()

        return f"✅ Tool '{name}' created and loaded!"

    def get_status(self) -> dict:
        """Get ecosystem status"""
        return {
            "router": self.router.get_stats(),
            "memory": get_tool_stats(),
            "sandbox_available": self.sandbox._sandbox_available,
            "evolved_tools_loaded": len(self.evolved_tools),
        }


def interactive_mode():
    """Run in interactive mode for testing"""
    twin = PrescientTwin(enable_full_agents=False)

    print("🎮 Interactive Mode - Type 'quit' to exit\n")
    print("Commands:")
    print("  evolve <task>  - Route a task to the best brain")
    print("  sandbox <code> - Execute code in sandbox")
    print("  status         - Show ecosystem status")
    print("  quit           - Exit\n")

    while True:
        try:
            user_input = input("🔮 > ").strip()

            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("👋 Goodbye!")
                break

            if user_input.lower() == "status":
                import json

                print(json.dumps(twin.get_status(), indent=2))
                continue

            if user_input.startswith("sandbox "):
                code = user_input[8:]
                result = twin.sandbox_execute(code)
                print(result)
                continue

            if user_input.startswith("evolve "):
                task = user_input[7:]
                result = twin.evolve(task)
                print(result)
                continue

            # Default: treat as evolution task
            result = twin.evolve(user_input)
            print(result)

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Prescient Twin Ecosystem")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument(
        "--full-agents", action="store_true", help="Enable full CodeAgents (slower)"
    )
    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    else:
        # Demo mode
        twin = PrescientTwin(enable_full_agents=args.full_agents)
        print("📊 Ecosystem Status:")
        import json

        print(json.dumps(twin.get_status(), indent=2))
