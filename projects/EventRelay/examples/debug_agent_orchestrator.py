#!/usr/bin/env python3
"""Debug agent orchestrator"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from youtube_extension.backend.containers.service_container import ServiceContainer

container = ServiceContainer()
orchestrator = container.get_service("agent_orchestrator")

print("🔍 Agent Orchestrator Debug:")
print(f"Agents: {orchestrator.list_agents()}")
print(f"Tasks: {orchestrator.list_task_types()}")
print(f"Agent types: {list(orchestrator._agent_types.keys())}")
print(f"Task mappings: {list(orchestrator._task_mappings.keys())}")