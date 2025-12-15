#!/usr/bin/env python3
"""
MCP Agent Network - Unified agent orchestration with MCP tool routing
Connects video-to-software pipeline agents with MCP servers
Anti-bloat: <100 lines per component, JSON config, no framework overhead
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# Agent Network Configuration
AGENT_NETWORK_CONFIG = Path(__file__).parent.parent.parent / "config" / "agent_network.json"

@dataclass
class MCPTool:
    """MCP tool available to agents"""
    name: str
    server: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class Agent:
    """Agent with MCP tool access"""
    id: str
    name: str
    role: str
    tools: List[str]  # MCP tool names
    capabilities: List[str]
    active: bool = True

class MCPAgentNetwork:
    """
    Unified network connecting agents to MCP servers.
    Routes requests through appropriate MCP tools based on agent capabilities.
    """

    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.tool_servers: Dict[str, str] = {}  # tool_name -> server_endpoint
        self._load_config()

    def _load_config(self):
        """Load or create network configuration"""
        if AGENT_NETWORK_CONFIG.exists():
            config = json.loads(AGENT_NETWORK_CONFIG.read_text())
            self._apply_config(config)
        else:
            self._create_default_config()

    def _create_default_config(self):
        """Create default agent network for video-to-software pipeline"""
        config = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "mcp_servers": {
                "youtube-extension": {
                    "endpoint": "http://127.0.0.1:8010",
                    "tools": ["process_video_markdown", "get_transcript", "analyze_video"]
                },
                "gemini-code-gen": {
                    "endpoint": "internal://ai_code_generator",
                    "tools": ["generate_fullstack", "determine_architecture", "generate_files"]
                },
                "github-deploy": {
                    "endpoint": "mcp://github",
                    "tools": ["create_repo", "push_code", "create_pr"]
                },
                "vercel-deploy": {
                    "endpoint": "https://api.vercel.com",
                    "tools": ["deploy_to_github_and_vercel", "deploy_project", "get_deployment_status"]
                },
                "skill-builder": {
                    "endpoint": "internal://skill_builder",
                    "tools": ["validate_build", "get_error_patterns", "learn_from_error", "suggest_fix"]
                },
                "knowledge-base": {
                    "endpoint": "internal://knowledge_base",
                    "tools": ["capture_technology", "get_capabilities", "get_context"]
                }
            },
            "agents": [
                {
                    "id": "video-ingest",
                    "name": "Video Ingest Agent",
                    "role": "Extract and analyze video content",
                    "tools": ["process_video_markdown", "get_transcript", "analyze_video"],
                    "capabilities": ["youtube_processing", "transcript_extraction", "content_analysis"]
                },
                {
                    "id": "architect",
                    "name": "Architecture Agent",
                    "role": "Determine tech stack and project structure",
                    "tools": ["determine_architecture", "get_context", "get_capabilities"],
                    "capabilities": ["architecture_design", "tech_selection", "knowledge_integration"]
                },
                {
                    "id": "code-gen",
                    "name": "Code Generation Agent",
                    "role": "Generate application code from specifications",
                    "tools": ["generate_fullstack", "generate_files", "get_error_patterns"],
                    "capabilities": ["code_generation", "fullstack_apps", "template_application"]
                },
                {
                    "id": "build-validator",
                    "name": "Build Validator Agent",
                    "role": "Test builds and fix errors",
                    "tools": ["validate_build", "get_error_patterns", "learn_from_error", "suggest_fix"],
                    "capabilities": ["build_testing", "error_resolution", "skill_learning"]
                },
                {
                    "id": "deployer",
                    "name": "Deployment Agent",
                    "role": "Deploy to GitHub and Vercel",
                    "tools": ["deploy_to_github_and_vercel", "create_repo", "push_code", "deploy_project", "get_deployment_status"],
                    "capabilities": ["github_deployment", "vercel_deployment", "ci_cd"]
                },
                {
                    "id": "knowledge-capture",
                    "name": "Knowledge Capture Agent",
                    "role": "Learn from each pipeline run",
                    "tools": ["capture_technology", "get_capabilities", "learn_from_error"],
                    "capabilities": ["continuous_learning", "pattern_recognition", "capability_generation"]
                }
            ]
        }

        AGENT_NETWORK_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        AGENT_NETWORK_CONFIG.write_text(json.dumps(config, indent=2))
        self._apply_config(config)
        logger.info(f"Created default agent network config: {AGENT_NETWORK_CONFIG}")

    def _apply_config(self, config: Dict):
        """Apply configuration to network"""
        # Register tools from MCP servers
        for server_name, server_config in config.get("mcp_servers", {}).items():
            endpoint = server_config.get("endpoint", "")
            for tool_name in server_config.get("tools", []):
                self.tools[tool_name] = MCPTool(
                    name=tool_name,
                    server=server_name,
                    description=f"Tool from {server_name}",
                    input_schema={}
                )
                self.tool_servers[tool_name] = endpoint

        # Register agents
        for agent_config in config.get("agents", []):
            self.agents[agent_config["id"]] = Agent(
                id=agent_config["id"],
                name=agent_config["name"],
                role=agent_config["role"],
                tools=agent_config.get("tools", []),
                capabilities=agent_config.get("capabilities", [])
            )

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)

    def get_agents_for_capability(self, capability: str) -> List[Agent]:
        """Find agents that have a specific capability"""
        return [a for a in self.agents.values() if capability in a.capabilities]

    def get_tool_endpoint(self, tool_name: str) -> Optional[str]:
        """Get MCP endpoint for a tool"""
        return self.tool_servers.get(tool_name)

    async def route_to_agent(self, agent_id: str, action: str, payload: Dict) -> Dict:
        """Route a request to an agent's MCP tools"""
        # Circuit Breaker / Rate Limiting
        if not self._check_rate_limit(agent_id):
            logger.warning(f"Rate limit exceeded for agent {agent_id}")
            return {"error": f"Rate limit exceeded for agent {agent_id}. Please try again later."}

        agent = self.get_agent(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}

        if action not in agent.tools:
            return {"error": f"Agent {agent_id} does not have tool {action}"}

        endpoint = self.get_tool_endpoint(action)
        if not endpoint:
            return {"error": f"No endpoint for tool {action}"}

        # Route based on endpoint type
        if endpoint.startswith("internal://"):
            return await self._call_internal(endpoint, action, payload)
        elif endpoint.startswith("mcp://"):
            return await self._call_mcp(endpoint, action, payload)
        else:
            return await self._call_http(endpoint, action, payload)

    async def _call_internal(self, endpoint: str, action: str, payload: Dict) -> Dict:
        """Call internal module"""
        module_name = endpoint.replace("internal://", "")
        logger.info(f"Internal call: {module_name}.{action}")

        # Route to actual internal tools
        try:
            if module_name == "ai_code_generator":
                return await self._call_code_generator(action, payload)
            elif module_name == "skill_builder":
                return await self._call_skill_builder(action, payload)
            elif module_name == "knowledge_base":
                return await self._call_knowledge_base(action, payload)
            else:
                return {"status": "routed", "module": module_name, "action": action}
        except Exception as e:
            return {"error": f"Internal tool error: {str(e)}"}

    async def _call_mcp(self, endpoint: str, action: str, payload: Dict) -> Dict:
        """Call MCP server via stdio/protocol"""
        server_name = endpoint.replace("mcp://", "")
        logger.info(f"MCP call: {server_name}.{action}")
        return {"status": "routed", "server": server_name, "action": action}

    async def _call_http(self, endpoint: str, action: str, payload: Dict) -> Dict:
        """Call HTTP endpoint"""
        logger.info(f"HTTP call: {endpoint}/{action}")

        # Route to YouTube extension (HTTP server at 127.0.0.1:8010)
        if endpoint.startswith("http://127.0.0.1:8010"):
            try:
                from .mcp_tools import get_youtube_tool
                youtube_tool = get_youtube_tool()

                # Route to specific tool method
                if action == "process_video_markdown":
                    return await youtube_tool.process_video_markdown(**payload)
                elif action == "get_transcript":
                    return await youtube_tool.get_transcript(**payload)
                elif action == "analyze_video":
                    return await youtube_tool.analyze_video(**payload)

            except Exception as e:
                logger.error(f"YouTube tool error: {e}")
                return {"error": f"YouTube tool error: {str(e)}"}

        # Route to Vercel API
        elif endpoint.startswith("https://api.vercel.com"):
            return await self._call_vercel_api(action, payload)

        return {"status": "routed", "endpoint": endpoint, "action": action}

    def get_pipeline_agents(self) -> List[str]:
        """Get ordered list of agents for video-to-software pipeline"""
        return ["video-ingest", "architect", "code-gen", "build-validator", "deployer", "knowledge-capture"]

    async def _call_code_generator(self, action: str, payload: Dict) -> Dict:
        """Call AI code generator (Gemini 3)"""
        logger.info(f"Code generator call: {action}")

        try:
            # Import existing AI code generator
            from youtube_extension.backend.ai_code_generator import AICodeGenerator
            generator = AICodeGenerator()

            # Route to specific method
            if action == "generate_fullstack":
                # Use existing generate_fullstack_project method
                video_analysis = payload.get("video_analysis", {})
                architecture = payload.get("architecture", {})

                project_config = {
                    "type": architecture.get("app_type", "web_app"),
                    "features": architecture.get("features", []),
                    "title": video_analysis.get("metadata", {}).get("title", "Generated App")
                }

                result = await generator.generate_fullstack_project(video_analysis, project_config)
                return {"status": "success", **result}

            else:
                return {"status": "unknown_action", "action": action}

        except Exception as e:
            logger.error(f"AI code generator error: {e}")
            return {"error": f"Code generator error: {str(e)}"}

    async def _call_skill_builder(self, action: str, payload: Dict) -> Dict:
        """Call skill builder and build validator"""
        logger.info(f"Skill builder call: {action}")

        try:
            # Route build validation actions
            if action == "validate_build":
                from .mcp_tools import get_build_validator_tool
                build_validator = get_build_validator_tool()
                return await build_validator.validate_build(**payload)

            # Other skill builder actions (error patterns, learning)
            else:
                # TODO: Implement other skill builder features
                return {"status": "pending_implementation", "action": action}

        except Exception as e:
            logger.error(f"Build validator error: {e}")
            return {"error": f"Build validator error: {str(e)}"}

    async def _call_knowledge_base(self, action: str, payload: Dict) -> Dict:
        """Call knowledge base"""
        logger.info(f"Knowledge base call: {action}")
        # TODO: Implement knowledge base integration
        return {"status": "pending_implementation", "action": action}

    async def _call_vercel_api(self, action: str, payload: Dict) -> Dict:
        """Call deployment tools (GitHub + Vercel)"""
        logger.info(f"Deployment call: {action}")

        try:
            # Route deployment actions
            if action == "deploy_to_github_and_vercel":
                from .mcp_tools import get_deployment_tool
                deployment_tool = get_deployment_tool()
                return await deployment_tool.deploy_to_github_and_vercel(**payload)

            # Other deployment actions
            elif action == "deploy_project":
                from .mcp_tools import get_deployment_tool
                deployment_tool = get_deployment_tool()
                return await deployment_tool.deploy_to_github_and_vercel(**payload)

            else:
                # TODO: Implement other deployment features
                return {"status": "pending_implementation", "action": action}

        except Exception as e:
            logger.error(f"Deployment error: {e}")
            return {"error": f"Deployment error: {str(e)}"}

    def get_network_status(self) -> Dict:
        """Get network status summary"""
        return {
            "agents": len(self.agents),
            "tools": len(self.tools),
            "servers": len(set(self.tool_servers.values())),
            "agent_ids": list(self.agents.keys()),
            "tool_names": list(self.tools.keys())
        }

    def _check_rate_limit(self, agent_id: str) -> bool:
        """
        Check if agent has exceeded rate limits (Circuit Breaker).
        Limit: 30 calls per minute per agent.
        """
        now = datetime.now().timestamp()
        if not hasattr(self, '_rate_limits'):
            self._rate_limits = {}  # agent_id -> [timestamps]
        
        history = self._rate_limits.get(agent_id, [])
        # Clean old entries (1 minute window)
        history = [t for t in history if now - t < 60]
        
        if len(history) >= 30:
            return False
            
        history.append(now)
        self._rate_limits[agent_id] = history
        return True

# Singleton instance
_network = None

def get_agent_network() -> MCPAgentNetwork:
    """Get or create the agent network singleton"""
    global _network
    if _network is None:
        _network = MCPAgentNetwork()
    return _network
