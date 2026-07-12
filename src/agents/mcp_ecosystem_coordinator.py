#!/usr/bin/env python3
"""
MCP Ecosystem Coordinator
Unified hub for coordinating all MCP servers in the YouTube extension ecosystem
"""

import abc
import asyncio
import importlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from youtube_extension.processors.enhanced_extractor import (
    EnhancedVideoExtractor,
    VideoContent,
)

# Add src/mcp to path for imports
# REMOVED: sys.path.append removed

logger = logging.getLogger(__name__)

class BaseMCPServer(abc.ABC):
    """Abstract base class for all MCP servers."""

    def __init__(self, name: str, server_type: str):
        self.name = name
        self.server_type = server_type
        self.status = "initialized"

    @abc.abstractmethod
    async def handle_request(self, request: dict) -> dict:
        """Handles an incoming request for the server."""
        pass

    @abc.abstractmethod
    def get_capabilities(self) -> dict:
        """Returns the capabilities/tools exposed by this server."""
        pass

    @abc.abstractmethod
    async def health_check(self) -> dict:
        """Performs a health check on the server."""
        pass

class MCPVideoProcessorServer(BaseMCPServer):
    """Handles video processing operations."""

    def __init__(self):
        super().__init__("video_processor", "video_processing")
        self.supported_formats = ["mp4", "webm", "avi"]
        # Initialize the Unified Pipeline Extractor
        self.extractor = EnhancedVideoExtractor()

    async def handle_request(self, request: dict) -> dict:
        """Process video processing requests."""
        action = request.get("action")
        video_id = request.get("video_id")

        if action == "process_video":
            logger.info(f"Processing video: {video_id}")
            try:
                # Use the Unified Pipeline (Gemini + Scoring)
                # Note: process_video expects a URL usually, but if ID is passed, we might need to construct URL
                # or ensure process_video handles IDs (it extracts ID from URL, so URL is safer)
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                content: VideoContent = await self.extractor.process_video(video_url)

                return {
                    "status": "success",
                    "result": content.summary,
                    "metadata": asdict(content.metadata),
                    "analysis": {
                        "topics": content.topics,
                        "sentiment": content.sentiment,
                        "world_class_score": content.world_class_analysis.get('quality_score') if content.world_class_analysis else None,
                        "actions": content.actions
                    }
                }
            except Exception as e:
                logger.error(f"Error in Unified Pipeline: {e}")
                return {"status": "error", "message": str(e)}

        elif action == "extract_transcript":
            logger.info(f"Extracting transcript for video: {video_id}")
            use_mock = os.getenv("USE_MOCK_SERVERS", "false").lower() == "true"
            if use_mock:
                return {
                    "status": "success",
                    "transcript": f"Transcript for video {video_id} (mock)",
                    "confidence": 0.95
                }
            return {"status": "error", "message": "Transcript extraction requires real connector; enable mock or route via backend."}
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def get_capabilities(self) -> dict:
        return {
            "tools": [
                {"name": "process_video", "description": "Processes a video by ID"},
                {"name": "extract_transcript", "description": "Extracts transcript from video"}
            ],
            "supported_formats": self.supported_formats
        }

    async def health_check(self) -> dict:
        return {"status": "healthy", "server": self.name}

class MCPYouTubeAPIProxyServer(BaseMCPServer):
    """Handles YouTube API operations."""

    def __init__(self):
        super().__init__("youtube_proxy", "api_proxy")
        self.api_endpoints = ["search", "videos", "channels"]

    async def handle_request(self, request: dict) -> dict:
        """Process YouTube API requests."""
        action = request.get("action")
        query = request.get("query")

        if action == "fetch_youtube_data":
            logger.info(f"Fetching YouTube data for query: {query}")
            return {
                "status": "success",
                "result": f"Data for '{query}' from YouTube API",
                "videos": [
                    {"id": "vid1", "title": f"Video about {query}", "views": 1000},
                    {"id": "vid2", "title": f"Another video about {query}", "views": 500}
                ]
            }
        elif action == "upload_video":
            video_data = request.get("video_data", {})
            logger.info(f"Uploading video: {video_data.get('video_id')}")
            return {
                "status": "success",
                "youtube_url": f"https://youtube.com/watch?v={video_data.get('video_id')}_uploaded"
            }
        else:
            return {"status": "error", "message": f"Unknown action: {action}"}

    def get_capabilities(self) -> dict:
        return {
            "tools": [
                {"name": "fetch_youtube_data", "description": "Fetches data from YouTube API"},
                {"name": "upload_video", "description": "Uploads video to YouTube"}
            ],
            "api_endpoints": self.api_endpoints
        }

    async def health_check(self) -> dict:
        return {"status": "healthy", "server": self.name}

class MCPEcosystemCoordinator:
    """Coordinates multiple MCP servers, routing requests and managing capabilities."""

    def __init__(self):
        self.servers: dict[str, BaseMCPServer] = {}
        self.capabilities_map: dict[str, dict] = {}
        self.workflow_history: list[dict] = []
        self.skill_registry = SkillRegistry()

    def list_skills(self, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns a list of discovered skills from the registry."""
        return self.skill_registry.list_skills(source=source)

    def register_server(self, server: BaseMCPServer) -> bool:
        """Registers an MCP server with the coordinator."""
        try:
            if server.name in self.servers:
                logger.warning(f"Server '{server.name}' already registered. Updating...")

            self.servers[server.name] = server
            self.capabilities_map[server.name] = server.get_capabilities()
            logger.info(f"✅ Registered server: {server.name} ({server.server_type})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register server {server.name}: {e}")
            return False

    async def discover_capabilities(self) -> dict:
        """Returns a consolidated view of all registered server capabilities."""
        all_capabilities = {
            "total_servers": len(self.servers),
            "servers": {},
            "available_tools": []
        }

        for name, caps in self.capabilities_map.items():
            all_capabilities["servers"][name] = caps
            if "tools" in caps:
                all_capabilities["available_tools"].extend(caps["tools"])

        return all_capabilities

    async def dispatch_request(self, server_name: str, request: dict) -> dict:
        """Dispatches a request to the specified MCP server."""
        server = self.servers.get(server_name)
        if not server:
            return {
                "status": "error",
                "message": f"Server '{server_name}' not found. Available servers: {list(self.servers.keys())}"
            }

        try:
            logger.info(f"🔄 Dispatching request to {server_name}: {request.get('action', 'unknown')}")
            result = await server.handle_request(request)

            # Log workflow history
            self.workflow_history.append({
                "timestamp": asyncio.get_event_loop().time(),
                "server": server_name,
                "request": request,
                "result": result
            })

            return result
        except Exception as e:
            logger.error(f"❌ Error dispatching to {server_name}: {e}")
            return {"status": "error", "message": str(e)}

    async def orchestrate_video_workflow(self, video_id: str) -> dict:
        """Orchestrates a complete video processing workflow."""
        logger.info(f"🎬 Starting video workflow for: {video_id}")

        workflow_steps = []

        # Step 1: Process video
        video_request = {"action": "process_video", "video_id": video_id}
        video_result = await self.dispatch_request("video_processor", video_request)
        workflow_steps.append({"step": "video_processing", "result": video_result})

        if video_result.get("status") != "success":
            return {"status": "failed", "message": "Video processing failed", "steps": workflow_steps}

        # Step 2: Extract transcript
        transcript_request = {"action": "extract_transcript", "video_id": video_id}
        transcript_result = await self.dispatch_request("video_processor", transcript_request)
        workflow_steps.append({"step": "transcript_extraction", "result": transcript_result})

        # Step 3: Upload to YouTube (if needed)
        upload_request = {
            "action": "upload_video",
            "video_data": {"video_id": video_id, "title": f"Processed {video_id}"}
        }
        upload_result = await self.dispatch_request("youtube_proxy", upload_request)
        workflow_steps.append({"step": "youtube_upload", "result": upload_result})

        return {
            "status": "success",
            "video_id": video_id,
            "workflow_steps": workflow_steps,
            "final_result": {
                "processed": video_result.get("result"),
                "transcript": transcript_result.get("transcript"),
                "youtube_url": upload_result.get("youtube_url")
            }
        }

    async def get_system_status(self) -> dict:
        """Provides comprehensive system status."""
        status = {
            "coordinator": "operational",
            "servers": {},
            "total_workflows": len(self.workflow_history)
        }

        for name, server in self.servers.items():
            try:
                health = await server.health_check()
                status["servers"][name] = health
            except Exception as e:
                status["servers"][name] = {"status": "error", "error": str(e)}

        return status


class SkillRegistry:
    """Registry for discovering and invoking GTM skills from skills-lock.json.

    Reads skill definitions from the lock file and dynamically loads skill
    classes for execution. Implements explicit env-var pass-through when
    spawning skill processes (no reliance on environment inheritance).
    """

    _LOCK_FILE = "skills-lock.json"

    def __init__(self, lock_file_path: Optional[str] = None):
        self._lock_path = Path(
            lock_file_path
            or os.environ.get("SKILLS_LOCK_PATH", "")
            or self._find_lock_file()
        )
        self._skills: dict[str, dict[str, Any]] = {}
        self._instances: dict[str, Any] = {}
        self._load_skills()

    def _find_lock_file(self) -> str:
        """Walk up from CWD or src/agents to find skills-lock.json."""
        candidates = [
            Path.cwd() / self._LOCK_FILE,
            Path(__file__).resolve().parents[2] / self._LOCK_FILE,
            Path(__file__).resolve().parents[3] / self._LOCK_FILE,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return self._LOCK_FILE

    def _load_skills(self) -> None:
        """Load GTM skill definitions from the lock file."""
        try:
            with open(self._lock_path) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning("Could not load skills-lock.json: %s", e)
            return

        skills_data = data.get("skills", {})
        for skill_id, meta in skills_data.items():
            # Only load uvai-skills (local GTM skills)
            if meta.get("source") == "uvai-skills" and meta.get("sourceType") == "local":
                self._skills[skill_id] = meta

        logger.info("Loaded %d GTM skills from %s", len(self._skills), self._lock_path)

    def _build_skill_metadata(self, skill_id: str, meta: dict[str, Any]) -> dict[str, Any]:
        """Build a normalized metadata dict for a skill entry."""
        return {
            "id": skill_id,
            "name": skill_id.replace("-", " ").title(),
            "class_name": meta.get("className", ""),
            "version": meta.get("version", "0.0.0"),
            "triggers": meta.get("triggers", []),
            "dependencies": meta.get("dependencies", []),
            "entry_point": meta.get("skillPath", ""),
        }

    def list_skills(self, source: Optional[str] = None) -> list[dict[str, Any]]:
        """Return metadata for all registered GTM skills, optionally filtered by source."""
        return [
            self._build_skill_metadata(skill_id, meta)
            for skill_id, meta in self._skills.items()
            if source is None or meta.get("source") == source
        ]

    def get_skill(self, skill_id: str) -> Optional[dict[str, Any]]:
        """Get metadata for a specific skill."""
        meta = self._skills.get(skill_id)
        if meta is None:
            return None
        return self._build_skill_metadata(skill_id, meta)

    def get_skills_for_trigger(self, event_type: str) -> list[dict[str, Any]]:
        """Return all skills that match a given trigger event."""
        return [
            self._build_skill_metadata(skill_id, meta)
            for skill_id, meta in self._skills.items()
            if event_type in meta.get("triggers", [])
        ]

    def _load_skill_instance(self, skill_id: str) -> Any:
        """Dynamically import and instantiate a skill class."""
        if skill_id in self._instances:
            return self._instances[skill_id]

        meta = self._skills.get(skill_id)
        if meta is None:
            raise ValueError(f"Unknown skill: {skill_id}")

        skill_path = meta["skillPath"]  # e.g. "src/skills/content_generation/main.py"
        class_name = meta["className"]  # e.g. "ContentGenerationSkill"

        # Convert file path to module path
        module_path = skill_path.replace("/", ".").removesuffix(".py")
        # Strip leading "src." if present since src is on sys.path
        if module_path.startswith("src."):
            module_path = module_path[4:]

        module = importlib.import_module(module_path)
        skill_class = getattr(module, class_name)
        instance = skill_class()
        self._instances[skill_id] = instance
        return instance

    def get_env_for_skill(self, skill_id: str) -> dict[str, str]:
        """Get the explicit env vars to pass through to a skill subprocess.

        Implements MCP security requirement: do NOT rely on environment
        inheritance; explicitly pass only required vars.
        """
        meta = self._skills.get(skill_id)
        if meta is None:
            return {}

        # Map dependency names to env vars
        dep_env_map: dict[str, list[str]] = {
            "gemini_service": ["GEMINI_API_KEY"],
            "database_service": ["DATABASE_URL"],
            "openai_service": ["OPENAI_API_KEY"],
        }

        env: dict[str, str] = {}
        for dep in meta.get("dependencies", []):
            for var in dep_env_map.get(dep, []):
                val = os.environ.get(var)
                if val is not None:
                    env[var] = val
        return env

    async def invoke_skill(
        self, skill_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke a skill by ID with the given payload.

        Returns the skill result as a dictionary.
        """
        try:
            instance = self._load_skill_instance(skill_id)
        except (ValueError, ImportError, AttributeError) as e:
            logger.error("Failed to load skill %s: %s", skill_id, e)
            return {"status": "error", "error": str(e)}

        try:
            result = await instance.execute(payload)
            return {
                "status": result.status,
                "output": result.output,
                "error": result.error,
            }
        except Exception as e:
            logger.error("Skill %s execution failed: %s", skill_id, e)
            return {"status": "error", "error": str(e)}


# Example usage and testing
async def main():
    """Main function for testing the MCP ecosystem coordinator."""
    coordinator = MCPEcosystemCoordinator()

    # Register servers
    video_processor = MCPVideoProcessorServer()
    youtube_proxy = MCPYouTubeAPIProxyServer()

    coordinator.register_server(video_processor)
    coordinator.register_server(youtube_proxy)

    # Discover capabilities
    print("\n--- Discovered Capabilities ---")
    capabilities = await coordinator.discover_capabilities()
    print(json.dumps(capabilities, indent=2))

    # Test individual requests
    print("\n--- Testing Individual Requests ---")
    video_request = {"action": "process_video", "video_id": "test_video_123"}
    response = await coordinator.dispatch_request("video_processor", video_request)
    print(f"Video processing response: {response}")

    youtube_request = {"action": "fetch_youtube_data", "query": "AI tutorials"}
    response = await coordinator.dispatch_request("youtube_proxy", youtube_request)
    print(f"YouTube API response: {response}")

    # Test orchestrated workflow
    print("\n--- Testing Orchestrated Workflow ---")
    workflow_result = await coordinator.orchestrate_video_workflow("workflow_test_456")
    print(f"Workflow result: {json.dumps(workflow_result, indent=2)}")

    # Get system status
    print("\n--- System Status ---")
    status = await coordinator.get_system_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
