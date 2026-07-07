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
import sys
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from youtube_extension.processors.enhanced_extractor import VideoContent

# Add src/mcp to path for imports
# REMOVED: sys.path.append removed

logger = logging.getLogger(__name__)
SKILLS_LOCK_FILE = Path(__file__).resolve().parents[2] / "skills-lock.json"

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
        self.extractor = None
        try:
            module = importlib.import_module(
                "youtube_extension.processors.enhanced_extractor"
            )
            EnhancedVideoExtractor = module.EnhancedVideoExtractor
            self.extractor = EnhancedVideoExtractor()
        except Exception as e:
            logger.warning(f"Enhanced extractor unavailable: {e}")

    async def handle_request(self, request: dict) -> dict:
        """Process video processing requests."""
        action = request.get("action")
        video_id = request.get("video_id")

        if action == "process_video":
            logger.info(f"Processing video: {video_id}")
            try:
                if self.extractor is None:
                    return {"status": "error", "message": "Video extractor unavailable"}
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


class SkillRegistry:
    """Registry for EventRelay GTM skills defined in skills-lock.json."""

    def __init__(self, lock_file: Path = SKILLS_LOCK_FILE):
        self.lock_file = Path(lock_file)
        self._skills: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.lock_file.exists():
            self._skills = []
            return

        data = json.loads(self.lock_file.read_text())
        candidates = [
            data.get("eventrelay_skills"),
            data.get("skills"),
            data.get("skills", {}).get("eventrelay_skills")
            if isinstance(data.get("skills"), dict)
            else None,
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                self._skills = candidate
                return
        self._skills = []

    def list_skills(self, trigger: str | None = None) -> list[dict[str, Any]]:
        if not trigger:
            return list(self._skills)
        return [s for s in self._skills if trigger in s.get("triggers", [])]

    def get_skill(self, skill_id: str) -> dict[str, Any] | None:
        for skill in self._skills:
            if skill.get("id") == skill_id:
                return skill
        return None

class MCPEcosystemCoordinator:
    """Coordinates multiple MCP servers, routing requests and managing capabilities."""

    def __init__(self, skill_registry: SkillRegistry | None = None):
        self.servers: dict[str, BaseMCPServer] = {}
        self.capabilities_map: dict[str, dict] = {}
        self.workflow_history: list[dict] = []
        self.skill_registry = skill_registry or SkillRegistry()

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
            "available_tools": [],
            "skills": self.skill_registry.list_skills(),
        }

        for name, caps in self.capabilities_map.items():
            all_capabilities["servers"][name] = caps
            if "tools" in caps:
                all_capabilities["available_tools"].extend(caps["tools"])

        return all_capabilities

    async def invoke_skill(
        self,
        skill_id: str,
        payload: dict[str, Any],
        env_vars: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Invoke a configured skill as a subprocess with explicit env pass-through."""
        skill = self.skill_registry.get_skill(skill_id)
        if not skill:
            return {"status": "error", "message": f"Skill '{skill_id}' not found"}

        entry_point = skill.get("entry_point")
        if not entry_point:
            return {"status": "error", "message": f"Skill '{skill_id}' has no entry_point"}
        entry_path = Path(entry_point)
        if not entry_path.is_absolute():
            entry_path = Path(__file__).resolve().parents[2] / entry_path

        required_env_vars = skill.get("required_env_vars", [])
        explicit_env = self._build_skill_env(required_env_vars, env_vars or {})
        missing_env_vars = [
            var_name for var_name in required_env_vars if var_name not in explicit_env
        ]
        if missing_env_vars:
            return {
                "status": "error",
                "message": f"Missing required env vars for skill '{skill_id}': {missing_env_vars}",
            }

        try:
            encoded_payload = json.dumps(payload).encode("utf-8")
        except TypeError as e:
            return {"status": "error", "message": f"Failed to serialize skill payload to JSON: {e}"}

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(entry_path),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=explicit_env,
        )
        stdout, stderr = await process.communicate(encoded_payload)

        if process.returncode != 0:
            return {
                "status": "error",
                "message": stderr.decode("utf-8").strip() or "Skill execution failed",
            }

        output = stdout.decode("utf-8").strip()
        if not output:
            return {"status": "success"}
        return json.loads(output)

    def _build_skill_env(
        self, required_env_vars: list[str], env_vars: dict[str, str]
    ) -> dict[str, str]:
        explicit_env = {}
        # Essential system variables needed by Python subprocesses.
        for var_name in ("PATH", "HOME", "USER", "PYTHONPATH"):
            var_value = os.getenv(var_name)
            if var_value:
                explicit_env[var_name] = var_value
        for var_name in required_env_vars:
            if var_name in env_vars:
                explicit_env[var_name] = env_vars[var_name]
            else:
                var_value = os.getenv(var_name)
                if var_value:
                    explicit_env[var_name] = var_value
        return explicit_env

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
