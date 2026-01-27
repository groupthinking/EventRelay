"""
Hybrid Model Router - Multi-Brain Intelligence

Assigns the right "Brain" (Gemini/Claude/Grok) to the right task.
This implements the "Prescient Twin" multi-model architecture.
"""

import os
import re
from typing import Optional, Dict, Any
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ModelBrain(Enum):
    """Available AI brains for routing"""

    GEMINI = "gemini"  # Visual reasoning specialist
    OPENAI = "openai"  # Code/reasoning specialist
    CLAUDE = "claude"  # Architecture & documentation specialist
    GROK = "grok"  # Real-time/edge specialist
    NVIDIA = "nvidia"  # GPU/optimization specialist
    PERPLEXITY = "perplexity"  # Search/research specialist
    LOCAL = "local"  # Local/open-source models (Qwen, etc.)


class HybridRouter:
    """
    Intelligent routing based on task characteristics.
    Routes tasks to the most appropriate AI model.
    """

    def __init__(self, enable_agents: bool = True):
        """
        Initialize the hybrid router.

        Args:
            enable_agents: If True, create full CodeAgents. If False, use lightweight mode.
        """
        self.enable_agents = enable_agents
        self.models = self._initialize_models()
        self.agents = self._initialize_agents() if enable_agents else {}
        self.routing_stats = {brain.value: 0 for brain in ModelBrain}

    def _initialize_models(self) -> Dict[str, Any]:
        """Initialize model configurations"""
        models = {}

        # Check which APIs are available
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            models["gemini"] = {
                "model_id": "gemini/gemini-2.5-flash",
                "available": True,
                "specialty": [
                    "video",
                    "image",
                    "visual",
                    "see",
                    "look",
                    "watch",
                    "multimodal",
                ],
            }
        else:
            models["gemini"] = {"available": False}

        if os.getenv("OPENAI_API_KEY"):
            models["openai"] = {
                "model_id": "openai/gpt-4o",
                "available": True,
                "specialty": [
                    "code",
                    "implement",
                    "debug",
                    "refactor",
                    "design",
                    "reasoning",
                ],
            }
        else:
            models["openai"] = {"available": False}

        if os.getenv("ANTHROPIC_API_KEY"):
            models["claude"] = {
                "model_id": "anthropic/claude-sonnet-4-20250514",
                "available": True,
                "specialty": ["architecture", "documentation", "review", "analysis"],
            }
        else:
            models["claude"] = {"available": False}

        if os.getenv("XAI_API_KEY"):
            models["grok"] = {
                "model_id": "xai/grok-2",
                "available": True,
                "specialty": [
                    "realtime",
                    "live",
                    "fast",
                    "quick",
                    "news",
                    "current",
                    "twitter",
                ],
            }
        else:
            models["grok"] = {"available": False}

        if os.getenv("NVIDIA_API_KEY"):
            models["nvidia"] = {
                "model_id": "nvidia/llama-3.3-70b-instruct",
                "available": True,
                "specialty": [
                    "optimize",
                    "gpu",
                    "performance",
                    "inference",
                    "hardware",
                ],
            }
        else:
            models["nvidia"] = {"available": False}

        if os.getenv("PERPLEXITY_API_KEY"):
            models["perplexity"] = {
                "model_id": "perplexity/llama-3.1-sonar-large-128k-online",
                "available": True,
                "specialty": [
                    "search",
                    "research",
                    "web",
                    "latest",
                    "facts",
                    "citations",
                ],
            }
        else:
            models["perplexity"] = {"available": False}

        # Local model as fallback (always available)
        models["local"] = {
            "model_id": "Qwen/Qwen2.5-Coder-32B-Instruct",
            "available": True,
            "specialty": ["general", "fallback"],
        }

        available = [k for k, v in models.items() if v.get("available")]
        print(f"🧠 Hybrid Router initialized with brains: {available}")

        return models

    def _initialize_agents(self) -> Dict[str, Any]:
        """Initialize CodeAgents for each available model"""
        agents = {}

        try:
            from smolagents import CodeAgent, LiteLLMModel, HfApiModel

            for name, config in self.models.items():
                if not config.get("available"):
                    continue

                try:
                    if name == "local":
                        model = HfApiModel(model_id=config["model_id"])
                    else:
                        model = LiteLLMModel(model_id=config["model_id"])

                    agents[name] = CodeAgent(
                        tools=[],  # Tools added later
                        model=model,
                        additional_authorized_imports=["os", "json", "datetime"],
                    )
                    print(f"  ✅ Agent initialized: {name}")

                except Exception as e:
                    print(f"  ⚠️  Failed to init {name} agent: {e}")

        except ImportError:
            print("⚠️  smolagents not available - router in lightweight mode")

        return agents

    def _detect_task_type(self, task: str) -> ModelBrain:
        """Analyze task text to determine best brain"""
        task_lower = task.lower()

        # Check each model's specialties
        for model_name, config in self.models.items():
            if not config.get("available"):
                continue

            specialties = config.get("specialty", [])
            for keyword in specialties:
                if keyword in task_lower:
                    return ModelBrain(model_name)

        # Default routing based on task patterns
        if any(
            word in task_lower for word in ["video", "image", "see", "visual", "watch"]
        ):
            return ModelBrain.GEMINI
        elif any(
            word in task_lower
            for word in ["code", "implement", "debug", "refactor", "design"]
        ):
            return ModelBrain.CLAUDE
        elif any(word in task_lower for word in ["fast", "realtime", "live", "news"]):
            return ModelBrain.GROK

        return ModelBrain.LOCAL

    def route(
        self, task: str, force_brain: Optional[ModelBrain] = None
    ) -> Dict[str, Any]:
        """
        Route a task to the appropriate brain.

        Args:
            task: The task description
            force_brain: Optionally force routing to a specific brain

        Returns:
            Dict with 'brain', 'result', and 'stats'
        """
        # Determine which brain to use
        if force_brain:
            brain = force_brain
        else:
            brain = self._detect_task_type(task)

        # Check if preferred brain is available
        if not self.models.get(brain.value, {}).get("available"):
            print(f"⚠️  {brain.value} not available, falling back to local")
            brain = ModelBrain.LOCAL

        self.routing_stats[brain.value] += 1
        print(f"🔀 Routing to {brain.value.upper()} (Specialist)")

        # Execute with agent if available
        if brain.value in self.agents:
            try:
                result = self.agents[brain.value].run(task)
                return {
                    "brain": brain.value,
                    "result": result,
                    "success": True,
                    "stats": self.routing_stats.copy(),
                }
            except Exception as e:
                return {
                    "brain": brain.value,
                    "result": f"Error: {str(e)}",
                    "success": False,
                    "stats": self.routing_stats.copy(),
                }
        else:
            return {
                "brain": brain.value,
                "result": f"[LIGHTWEIGHT MODE] Task queued for {brain.value}: {task[:100]}...",
                "success": True,
                "stats": self.routing_stats.copy(),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "routing_counts": self.routing_stats,
            "available_brains": [
                k for k, v in self.models.items() if v.get("available")
            ],
            "agents_active": list(self.agents.keys()),
        }


# Quick test
if __name__ == "__main__":
    router = HybridRouter(enable_agents=False)  # Lightweight mode for testing

    print("\n📊 Testing routing logic:")
    test_tasks = [
        "Analyze this video for motion patterns",
        "Refactor the database module to use async",
        "What's the latest news about AI?",
        "Calculate the meaning of life",
    ]

    for task in test_tasks:
        result = router.route(task)
        print(f"  '{task[:40]}...' → {result['brain']}")

    print(f"\n📈 Stats: {router.get_stats()}")
