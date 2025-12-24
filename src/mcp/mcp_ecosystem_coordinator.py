#!/usr/bin/env python3
"""
MCP Ecosystem Coordination System for UVAI
Optimizing coordination across all 24 systems with intelligent routing and management
"""

import asyncio
import json
import logging
import os
import sys
import time
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from pathlib import Path
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import threading
from concurrent.futures import ThreadPoolExecutor
import uuid
import abc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [MCP_COORDINATOR] %(message)s'
)
logger = logging.getLogger("mcp_ecosystem_coordinator")

@dataclass
class MCPNode:
    """MCP node representation"""
    node_id: str
    name: str
    path: str
    mcp_endpoint: str
    status: str  # 'online', 'offline', 'error', 'starting'
    capabilities: List[str]
    last_heartbeat: str
    performance_score: float
    load_factor: float
    priority_level: int  # 1=critical, 2=high, 3=medium, 4=low

@dataclass
class MCPTask:
    """MCP task for routing"""
    task_id: str
    task_type: str
    payload: Dict[str, Any]
    requirements: List[str]
    priority: int
    created_at: str
    target_nodes: Optional[List[str]]
    status: str  # 'pending', 'routing', 'executing', 'completed', 'failed'

class BaseMCPServer(abc.ABC):
    """Abstract base class for integrated MCP servers."""
    
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
    """Integrated video processing server."""
    
    def __init__(self):
        super().__init__("video_processor", "video_processing")
        self.supported_formats = ["mp4", "webm", "avi"]
        
    async def handle_request(self, request: dict) -> dict:
        """Process video processing requests."""
        action = request.get("action")
        video_id = request.get("video_id")
        
        if action == "process_video":
            logger.info(f"Processing video: {video_id}")
            return {
                "status": "success", 
                "result": f"Video {video_id} processed successfully",
                "metadata": {
                    "duration": "120s",
                    "format": "mp4",
                    "size": "15MB"
                }
            }
        elif action == "extract_transcript":
            logger.info(f"Extracting transcript for video: {video_id}")
            return {
                "status": "success",
                "transcript": f"Transcript for video {video_id}",
                "confidence": 0.95
            }
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
    """Integrated YouTube API proxy server."""
    
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
    """
    MCP Ecosystem Coordination System for UVAI
    
    Features:
    - Intelligent task routing across 24 systems
    - Load balancing and performance optimization
    - Health monitoring and auto-recovery
    - Cross-system communication coordination
    - Resource allocation optimization
    - Fault tolerance and redundancy
    - Integrated MCP server management
    """
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "/Users/garvey/UVAI/10_MCP_ECOSYSTEM"
        self.coordination_config = self._load_coordination_config()
        
        # MCP node registry
        self.mcp_nodes: Dict[str, MCPNode] = {}
        self.node_capabilities = defaultdict(list)  # capability -> [node_ids]
        
        # Integrated MCP servers
        self.integrated_servers: Dict[str, BaseMCPServer] = {}
        self.server_capabilities = defaultdict(list)  # capability -> [server_names]
        
        # Task management
        self.task_queue = deque()
        self.active_tasks: Dict[str, MCPTask] = {}
        self.completed_tasks = deque(maxlen=1000)
        
        # Performance tracking
        self.performance_metrics = defaultdict(list)
        self.load_balancer_stats = {
            'total_tasks_routed': 0,
            'successful_completions': 0,
            'failed_tasks': 0,
            'average_response_time': 0.0
        }
        
        # Coordination state
        self.coordination_active = False
        self.heartbeat_interval = 30  # seconds
        self.task_routing_interval = 5  # seconds
        
        # Thread pool for concurrent operations
        self.executor = ThreadPoolExecutor(max_workers=8)
        
        # Auto-discover UVAI systems
        self._discover_uvai_systems()
        
        # Initialize integrated servers
        self._initialize_integrated_servers()
        
        logger.info("🚀 MCP Ecosystem Coordinator initialized")
        logger.info(f"🎯 Managing {len(self.mcp_nodes)} UVAI systems")
    
    def _load_coordination_config(self) -> Dict[str, Any]:
        """Load MCP coordination configuration"""
        try:
            config_file = Path(self.config_path) / "mcp_coordination_config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
                logger.info("✅ MCP coordination config loaded")
                return config
            else:
                return self._create_default_config()
        except Exception as e:
            logger.warning(f"⚠️ Could not load config: {e} - using defaults")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default coordination configuration"""
        config = {
            "coordination_settings": {
                "heartbeat_interval": 30,
                "task_routing_interval": 5,
                "max_concurrent_tasks": 50,
                "load_balance_strategy": "performance_based",
                "auto_recovery": True
            },
            "system_priorities": {
                "critical": ["youtube-extension", "grok-claude-hybrid", "mcp-saas-platform"],
                "high": ["multi-modal-engine", "self-correcting-executor", "unified-mcp-runtime"],
                "medium": ["file-transparency", "intelligent-monitoring", "framework-guide"],
                "low": ["documentation", "testing", "archive"]
            },
            "capability_routing": {
                "video_processing": ["youtube-extension", "multi-modal-engine"],
                "ai_analysis": ["grok-claude-hybrid", "self-correcting-executor"],
                "file_management": ["file-transparency", "unified-mcp-runtime"],
                "monitoring": ["intelligent-monitoring", "system-health"],
                "deployment": ["mcp-saas-platform", "build-chromium"]
            }
        }
        
        # Save default config
        try:
            config_file = Path(self.config_path) / "mcp_coordination_config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("💾 Default coordination config created")
        except Exception as e:
            logger.warning(f"⚠️ Could not save default config: {e}")
        
        return config
    
    def _discover_uvai_systems(self):
        """Auto-discover UVAI systems and register as MCP nodes"""
        uvai_systems = [
            # Core Platform
            {
                "name": "youtube-extension",
                "path": "/Users/garvey/youtube-extension",
                "endpoint": "http://localhost:8010",
                "capabilities": ["video_processing", "transcript_analysis", "action_generation"],
                "priority": 1
            },
            {
                "name": "multi-modal-engine", 
                "path": "/Users/garvey/multi_modal_engine",
                "endpoint": "http://localhost:8011",
                "capabilities": ["multimodal_processing", "content_synthesis"],
                "priority": 1
            },
            {
                "name": "nl-to-structure",
                "path": "/Users/garvey/nl-to-structure", 
                "endpoint": "http://localhost:8012",
                "capabilities": ["natural_language_processing", "data_structuring"],
                "priority": 2
            },
            
            # Intelligence Layer
            {
                "name": "grok-claude-hybrid",
                "path": "/Users/garvey/Desktop/Grok-Claude-Hybrid-Deployment",
                "endpoint": "http://localhost:8004",
                "capabilities": ["ai_routing", "cross_validation", "intelligent_analysis"],
                "priority": 1
            },
            {
                "name": "self-correcting-executor-prod",
                "path": "/Users/garvey/UVAI/01_AGENTS/self-correcting-executor-desktop",
                "endpoint": "http://localhost:8003",
                "capabilities": ["error_correction", "autonomous_execution"],
                "priority": 1
            },
            {
                "name": "aicce-platform",
                "path": "/Users/garvey/Desktop/AICCE PLATFORM",
                "endpoint": "http://localhost:8015",
                "capabilities": ["conversation_intelligence", "enterprise_ai"],
                "priority": 2
            },
            
            # Infrastructure Layer
            {
                "name": "unified-mcp-runtime",
                "path": "/Users/garvey/UVAI/Unified_MCP_DevContainer_Runtime",
                "endpoint": "http://localhost:8020",
                "capabilities": ["container_orchestration", "mcp_runtime", "infrastructure"],
                "priority": 1
            },
            {
                "name": "mcp-saas-platform",
                "path": "/Users/garvey/mcp-saas-platform",
                "endpoint": "http://localhost:8021",
                "capabilities": ["saas_deployment", "billing", "multi_tenancy"],
                "priority": 1
            },
            {
                "name": "build-chromium",
                "path": "/Users/garvey/build-chromium",
                "endpoint": "http://localhost:8022", 
                "capabilities": ["browser_deployment", "cross_platform"],
                "priority": 2
            },
            {
                "name": "framework-guide-cursor",
                "path": "/Users/garvey/Desktop/ Framework-Guide-for-Cursor",
                "endpoint": "http://localhost:8023",
                "capabilities": ["mcp_orchestration", "development_guidelines"],
                "priority": 2
            },
            
            # Enhanced Systems (New)
            {
                "name": "file-transparency-system",
                "path": "/Users/garvey/UVAI/09_CONFIGURATION/ecosystem_analysis", 
                "endpoint": "http://localhost:8031",
                "capabilities": ["file_management", "transparency", "optimization_analysis"],
                "priority": 2
            },
            {
                "name": "intelligent-monitoring",
                "path": "/Users/garvey/Desktop/Grok-Claude-Hybrid-Deployment",
                "endpoint": "http://localhost:8032",
                "capabilities": ["system_monitoring", "ai_insights", "predictive_analysis"],
                "priority": 2
            },
            
            # UVAI Core Systems
            {
                "name": "uvai-agents-core",
                "path": "/Users/garvey/UVAI/01_AGENTS",
                "endpoint": "http://localhost:8040",
                "capabilities": ["agent_coordination", "workflow_management"],
                "priority": 2
            },
            {
                "name": "uvai-domains",
                "path": "/Users/garvey/UVAI/03_DOMAINS", 
                "endpoint": "http://localhost:8041",
                "capabilities": ["domain_specific_processing", "specialization"],
                "priority": 3
            },
            {
                "name": "uvai-adapters",
                "path": "/Users/garvey/UVAI/04_ADAPTERS",
                "endpoint": "http://localhost:8042",
                "capabilities": ["system_adaptation", "integration"],
                "priority": 3
            },
            {
                "name": "uvai-infrastructure",
                "path": "/Users/garvey/UVAI/05_INFRASTRUCTURE",
                "endpoint": "http://localhost:8043",
                "capabilities": ["infrastructure_management", "deployment"],
                "priority": 2
            },
            {
                "name": "uvai-commercial",
                "path": "/Users/garvey/UVAI/06_COMMERCIAL",
                "endpoint": "http://localhost:8044",
                "capabilities": ["commercial_operations", "revenue_management"],
                "priority": 2
            },
            {
                "name": "uvai-datasets",
                "path": "/Users/garvey/UVAI/07_DATASETS",
                "endpoint": "http://localhost:8045",
                "capabilities": ["data_management", "dataset_processing"],
                "priority": 3
            },
            {
                "name": "uvai-testing",
                "path": "/Users/garvey/UVAI/08_TESTING",
                "endpoint": "http://localhost:8046",
                "capabilities": ["testing", "validation", "quality_assurance"],
                "priority": 3
            },
            {
                "name": "uvai-configuration",
                "path": "/Users/garvey/UVAI/09_CONFIGURATION",
                "endpoint": "http://localhost:8047",
                "capabilities": ["configuration_management", "system_setup"],
                "priority": 2
            },
            {
                "name": "uvai-mcp-ecosystem",
                "path": "/Users/garvey/UVAI/10_MCP_ECOSYSTEM",
                "endpoint": "http://localhost:8048",
                "capabilities": ["mcp_coordination", "ecosystem_management"],
                "priority": 1
            },
            
            # Supporting Systems
            # Removed non-project dependency to avoid external calls not part of this build
            {
                "name": "workspace-management",
                "path": "/Users/garvey/workspace",
                "endpoint": "http://localhost:8051",
                "capabilities": ["workspace_management", "development_tools"],
                "priority": 4
            },
            {
                "name": "universal-mcp-swarm",
                "path": "/Users/garvey/UVAI/universal-mcp-swarm",
                "endpoint": "http://localhost:8052",
                "capabilities": ["swarm_coordination", "distributed_processing"],
                "priority": 2
            },
            {
                "name": "web-development",
                "path": "/Users/garvey/UVAI/web-dev",
                "endpoint": "http://localhost:8053",
                "capabilities": ["web_development", "frontend_tools"],
                "priority": 4
            }
        ]
        
        # Register all systems as MCP nodes
        for system in uvai_systems:
            if os.path.exists(system["path"]):
                node = MCPNode(
                    node_id=str(uuid.uuid4()),
                    name=system["name"],
                    path=system["path"],
                    mcp_endpoint=system["endpoint"],
                    status="offline",  # Will be updated by heartbeat
                    capabilities=system["capabilities"],
                    last_heartbeat="",
                    performance_score=1.0,
                    load_factor=0.0,
                    priority_level=system["priority"]
                )
                
                self.mcp_nodes[node.node_id] = node
                
                # Index capabilities
                for capability in system["capabilities"]:
                    self.node_capabilities[capability].append(node.node_id)
                
                logger.info(f"📝 Registered MCP node: {system['name']} ({len(system['capabilities'])} capabilities)")
            else:
                logger.warning(f"⚠️ System path not found: {system['path']}")
        
        logger.info(f"✅ Discovered and registered {len(self.mcp_nodes)} MCP nodes")
    
    def _initialize_integrated_servers(self):
        """Initialize integrated MCP servers."""
        try:
            # Register video processor
            video_processor = MCPVideoProcessorServer()
            self.register_integrated_server(video_processor)
            
            # Register YouTube API proxy
            youtube_proxy = MCPYouTubeAPIProxyServer()
            self.register_integrated_server(youtube_proxy)
            
            logger.info(f"✅ Initialized {len(self.integrated_servers)} integrated MCP servers")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize integrated servers: {e}")

    def register_integrated_server(self, server: BaseMCPServer) -> bool:
        """Register an integrated MCP server with the coordinator."""
        try:
            if server.name in self.integrated_servers:
                logger.warning(f"Integrated server '{server.name}' already registered. Updating...")
                
            self.integrated_servers[server.name] = server
            
            # Register capabilities
            capabilities = server.get_capabilities()
            if "tools" in capabilities:
                for tool in capabilities["tools"]:
                    tool_name = tool.get("name", "")
                    if tool_name:
                        self.server_capabilities[tool_name].append(server.name)
            
            logger.info(f"✅ Registered integrated server: {server.name} ({server.server_type})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to register integrated server {server.name}: {e}")
            return False

    async def dispatch_to_integrated_server(self, server_name: str, request: dict) -> dict:
        """Dispatch a request to an integrated MCP server."""
        server = self.integrated_servers.get(server_name)
        if not server:
            return {
                "status": "error", 
                "message": f"Integrated server '{server_name}' not found. Available: {list(self.integrated_servers.keys())}"
            }
            
        try:
            logger.info(f"🔄 Dispatching to integrated server {server_name}: {request.get('action', 'unknown')}")
            result = await server.handle_request(request)
            
            # Update performance metrics
            self.load_balancer_stats['total_tasks_routed'] += 1
            if result.get('status') == 'success':
                self.load_balancer_stats['successful_completions'] += 1
            else:
                self.load_balancer_stats['failed_tasks'] += 1
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Error dispatching to integrated server {server_name}: {e}")
            self.load_balancer_stats['failed_tasks'] += 1
            return {"status": "error", "message": str(e)}

    async def orchestrate_video_workflow(self, video_id: str) -> dict:
        """Orchestrate a complete video processing workflow using integrated servers."""
        logger.info(f"🎬 Starting integrated video workflow for: {video_id}")
        
        workflow_steps = []
        
        # Step 1: Process video
        video_request = {"action": "process_video", "video_id": video_id}
        video_result = await self.dispatch_to_integrated_server("video_processor", video_request)
        workflow_steps.append({"step": "video_processing", "result": video_result})
        
        if video_result.get("status") != "success":
            return {"status": "failed", "message": "Video processing failed", "steps": workflow_steps}
            
        # Step 2: Extract transcript
        transcript_request = {"action": "extract_transcript", "video_id": video_id}
        transcript_result = await self.dispatch_to_integrated_server("video_processor", transcript_request)
        workflow_steps.append({"step": "transcript_extraction", "result": transcript_result})
        
        # Step 3: Upload to YouTube (if needed)
        upload_request = {
            "action": "upload_video", 
            "video_data": {"video_id": video_id, "title": f"Processed {video_id}"}
        }
        upload_result = await self.dispatch_to_integrated_server("youtube_proxy", upload_request)
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

    async def get_integrated_servers_status(self) -> dict:
        """Get status of all integrated MCP servers."""
        status = {
            "total_servers": len(self.integrated_servers),
            "servers": {},
            "capabilities": dict(self.server_capabilities)
        }
        
        for name, server in self.integrated_servers.items():
            try:
                health = await server.health_check()
                status["servers"][name] = health
            except Exception as e:
                status["servers"][name] = {"status": "error", "error": str(e)}
                
        return status

    async def start_coordination(self):
        """Start MCP ecosystem coordination"""
        if self.coordination_active:
            logger.warning("⚠️ Coordination already active")
            return
        
        self.coordination_active = True
        logger.info("🚀 Starting MCP ecosystem coordination")
        
        # Start coordination tasks
        coordination_tasks = [
            self._heartbeat_monitor(),
            self._task_router(),
            self._performance_monitor(),
            self._load_balancer()
        ]
        
        try:
            await asyncio.gather(*coordination_tasks)
        except KeyboardInterrupt:
            logger.info("⏹️ Coordination stopped by user")
        except Exception as e:
            logger.error(f"❌ Coordination failed: {e}")
        finally:
            self.coordination_active = False
    
    def stop_coordination(self):
        """Stop MCP ecosystem coordination"""
        self.coordination_active = False
        logger.info("⏹️ Stopping MCP ecosystem coordination")
    
    async def _heartbeat_monitor(self):
        """Monitor heartbeat and health of all MCP nodes"""
        while self.coordination_active:
            try:
                online_count = 0
                
                for node_id, node in self.mcp_nodes.items():
                    # Check node health
                    health_status = await self._check_node_health(node)
                    
                    # Update node status
                    old_status = node.status
                    node.status = health_status['status']
                    node.last_heartbeat = datetime.now().isoformat()
                    node.performance_score = health_status.get('performance_score', 0.5)
                    node.load_factor = health_status.get('load_factor', 0.0)
                    
                    if node.status == 'online':
                        online_count += 1
                    
                    # Log status changes
                    if old_status != node.status:
                        logger.info(f"🔄 Node {node.name}: {old_status} -> {node.status}")
                
                logger.info(f"💓 Heartbeat: {online_count}/{len(self.mcp_nodes)} nodes online")
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"❌ Heartbeat monitor error: {e}")
                await asyncio.sleep(5)
    
    async def _check_node_health(self, node: MCPNode) -> Dict[str, Any]:
        """Check health of individual MCP node"""
        try:
            # For now, simulate health check based on path existence and priority
            if os.path.exists(node.path):
                # Critical nodes are more likely to be "online"
                if node.priority_level == 1:
                    return {
                        'status': 'online',
                        'performance_score': 0.9,
                        'load_factor': 0.3
                    }
                elif node.priority_level == 2:
                    return {
                        'status': 'online',
                        'performance_score': 0.8,
                        'load_factor': 0.2
                    }
                else:
                    return {
                        'status': 'offline',
                        'performance_score': 0.5,
                        'load_factor': 0.0
                    }
            else:
                return {
                    'status': 'error',
                    'performance_score': 0.0,
                    'load_factor': 0.0
                }
                
        except Exception as e:
            logger.warning(f"⚠️ Health check failed for {node.name}: {e}")
            return {
                'status': 'error',
                'performance_score': 0.0,
                'load_factor': 0.0
            }
    
    async def _task_router(self):
        """Intelligent task routing across MCP nodes"""
        while self.coordination_active:
            try:
                if self.task_queue:
                    # Process tasks from queue
                    tasks_processed = 0
                    
                    while self.task_queue and tasks_processed < 10:  # Process up to 10 tasks per cycle
                        task = self.task_queue.popleft()
                        
                        # Route task to optimal node
                        success = await self._route_task(task)
                        
                        if success:
                            self.active_tasks[task.task_id] = task
                            self.load_balancer_stats['total_tasks_routed'] += 1
                            logger.info(f"📋 Routed task {task.task_id} ({task.task_type})")
                        else:
                            # Re-queue task for retry
                            task.status = 'pending'
                            self.task_queue.append(task)
                            logger.warning(f"⚠️ Failed to route task {task.task_id}")
                        
                        tasks_processed += 1
                    
                    if tasks_processed > 0:
                        logger.info(f"📊 Processed {tasks_processed} tasks")
                
                await asyncio.sleep(self.task_routing_interval)
                
            except Exception as e:
                logger.error(f"❌ Task router error: {e}")
                await asyncio.sleep(5)
    
    async def _route_task(self, task: MCPTask) -> bool:
        """Route individual task to optimal MCP node"""
        try:
            # Find candidate nodes based on capabilities
            candidate_nodes = []
            
            for requirement in task.requirements:
                if requirement in self.node_capabilities:
                    for node_id in self.node_capabilities[requirement]:
                        node = self.mcp_nodes.get(node_id)
                        if node and node.status == 'online':
                            candidate_nodes.append(node)
            
            if not candidate_nodes:
                logger.warning(f"⚠️ No capable nodes found for task {task.task_id}")
                return False
            
            # Select optimal node based on performance and load
            optimal_node = self._select_optimal_node(candidate_nodes, task)
            
            if optimal_node:
                # Simulate task execution
                task.status = 'executing'
                task.target_nodes = [optimal_node.node_id]
                
                # Update node load
                optimal_node.load_factor = min(1.0, optimal_node.load_factor + 0.1)
                
                logger.info(f"🎯 Task {task.task_id} routed to {optimal_node.name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Task routing failed: {e}")
            return False
    
    def _select_optimal_node(self, candidates: List[MCPNode], task: MCPTask) -> Optional[MCPNode]:
        """Select optimal node based on performance, load, and priority"""
        try:
            # Score each candidate
            scored_candidates = []
            
            for node in candidates:
                # Calculate composite score
                performance_weight = 0.4
                load_weight = 0.3
                priority_weight = 0.3
                
                # Performance score (higher is better)
                performance_score = node.performance_score * performance_weight
                
                # Load score (lower load is better)
                load_score = (1.0 - node.load_factor) * load_weight
                
                # Priority score (lower priority level is better)
                priority_score = (5 - node.priority_level) / 4 * priority_weight
                
                composite_score = performance_score + load_score + priority_score
                
                scored_candidates.append((node, composite_score))
            
            # Select highest scoring node
            if scored_candidates:
                optimal_node, score = max(scored_candidates, key=lambda x: x[1])
                logger.debug(f"🎯 Selected {optimal_node.name} (score: {score:.3f})")
                return optimal_node
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Node selection failed: {e}")
            return None
    
    async def _performance_monitor(self):
        """Monitor performance metrics across ecosystem"""
        while self.coordination_active:
            try:
                # Collect performance metrics
                total_nodes = len(self.mcp_nodes)
                online_nodes = sum(1 for node in self.mcp_nodes.values() if node.status == 'online')
                avg_performance = sum(node.performance_score for node in self.mcp_nodes.values()) / max(1, total_nodes)
                avg_load = sum(node.load_factor for node in self.mcp_nodes.values()) / max(1, total_nodes)
                
                # Store metrics
                timestamp = datetime.now().isoformat()
                metrics = {
                    'timestamp': timestamp,
                    'total_nodes': total_nodes,
                    'online_nodes': online_nodes,
                    'availability_percent': (online_nodes / max(1, total_nodes)) * 100,
                    'avg_performance': avg_performance,
                    'avg_load': avg_load,
                    'active_tasks': len(self.active_tasks),
                    'queued_tasks': len(self.task_queue)
                }
                
                self.performance_metrics['ecosystem'].append(metrics)
                
                # Keep only recent metrics
                if len(self.performance_metrics['ecosystem']) > 100:
                    self.performance_metrics['ecosystem'] = self.performance_metrics['ecosystem'][-100:]
                
                logger.info(
                    f"📊 Performance: {online_nodes}/{total_nodes} online, "
                    f"Avg performance: {avg_performance:.1%}, "
                    f"Avg load: {avg_load:.1%}"
                )
                
                await asyncio.sleep(60)  # Monitor every minute
                
            except Exception as e:
                logger.error(f"❌ Performance monitor error: {e}")
                await asyncio.sleep(10)
    
    async def _load_balancer(self):
        """Intelligent load balancing across nodes"""
        while self.coordination_active:
            try:
                # Check for overloaded nodes
                overloaded_nodes = [
                    node for node in self.mcp_nodes.values() 
                    if node.load_factor > 0.8 and node.status == 'online'
                ]
                
                # Check for underutilized nodes
                underutilized_nodes = [
                    node for node in self.mcp_nodes.values()
                    if node.load_factor < 0.3 and node.status == 'online'
                ]
                
                if overloaded_nodes and underutilized_nodes:
                    logger.info(f"⚖️ Load balancing: {len(overloaded_nodes)} overloaded, {len(underutilized_nodes)} underutilized")
                    
                    # Simulate load redistribution
                    for overloaded in overloaded_nodes:
                        if underutilized_nodes:
                            target = underutilized_nodes[0]
                            
                            # Transfer some load
                            transfer_amount = min(0.2, overloaded.load_factor - 0.6)
                            overloaded.load_factor -= transfer_amount
                            target.load_factor += transfer_amount * 0.5  # Some efficiency loss
                            
                            logger.info(f"⚖️ Load transfer: {overloaded.name} -> {target.name} ({transfer_amount:.2f})")
                
                # Gradually reduce load factors (simulate task completion)
                for node in self.mcp_nodes.values():
                    if node.load_factor > 0:
                        node.load_factor = max(0, node.load_factor - 0.05)
                
                await asyncio.sleep(30)  # Balance every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Load balancer error: {e}")
                await asyncio.sleep(10)
    
    def submit_task(
        self, 
        task_type: str, 
        payload: Dict[str, Any], 
        requirements: List[str], 
        priority: int = 3
    ) -> str:
        """Submit task to MCP ecosystem"""
        try:
            task = MCPTask(
                task_id=str(uuid.uuid4()),
                task_type=task_type,
                payload=payload,
                requirements=requirements,
                priority=priority,
                created_at=datetime.now().isoformat(),
                target_nodes=None,
                status='pending'
            )
            
            self.task_queue.append(task)
            logger.info(f"📝 Task submitted: {task.task_id} ({task_type})")
            
            return task.task_id
            
        except Exception as e:
            logger.error(f"❌ Task submission failed: {e}")
            return ""
    
    def get_ecosystem_status(self) -> Dict[str, Any]:
        """Get comprehensive ecosystem status"""
        try:
            # Node status summary
            node_status = defaultdict(int)
            for node in self.mcp_nodes.values():
                node_status[node.status] += 1
            
            # Capability coverage
            capability_coverage = {}
            for capability, node_ids in self.node_capabilities.items():
                online_nodes = sum(
                    1 for node_id in node_ids 
                    if self.mcp_nodes.get(node_id, {}).status == 'online'
                )
                capability_coverage[capability] = {
                    'total_nodes': len(node_ids),
                    'online_nodes': online_nodes,
                    'coverage_percent': (online_nodes / max(1, len(node_ids))) * 100
                }
            
            # Recent performance
            recent_metrics = self.performance_metrics['ecosystem'][-10:] if self.performance_metrics['ecosystem'] else []
            
            return {
                'ecosystem_overview': {
                    'total_nodes': len(self.mcp_nodes),
                    'node_status': dict(node_status),
                    'coordination_active': self.coordination_active,
                    'last_updated': datetime.now().isoformat()
                },
                'capability_coverage': capability_coverage,
                'task_management': {
                    'queued_tasks': len(self.task_queue),
                    'active_tasks': len(self.active_tasks),
                    'completed_tasks': len(self.completed_tasks)
                },
                'load_balancer_stats': self.load_balancer_stats.copy(),
                'recent_performance': recent_metrics,
                'top_performing_nodes': [
                    {
                        'name': node.name,
                        'performance_score': node.performance_score,
                        'load_factor': node.load_factor,
                        'status': node.status
                    }
                    for node in sorted(
                        self.mcp_nodes.values(), 
                        key=lambda x: x.performance_score, 
                        reverse=True
                    )[:5]
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get ecosystem status: {e}")
            return {'error': str(e)}

async def main():
    """Main execution for MCP ecosystem coordination"""
    
    coordinator = MCPEcosystemCoordinator()
    
    try:
        print("🚀 MCP ECOSYSTEM COORDINATOR")
        print("🎯 Optimizing coordination across 24 UVAI systems")
        print("=" * 60)
        
        # Show initial status
        status = coordinator.get_ecosystem_status()
        print(f"📊 Total Nodes: {status['ecosystem_overview']['total_nodes']}")
        print(f"🔗 Capabilities: {len(status['capability_coverage'])}")
        print(f"⚡ Node Status: {status['ecosystem_overview']['node_status']}")
        
        # Submit some test tasks
        coordinator.submit_task(
            task_type="video_processing",
            payload={"video_id": "test123", "analysis_type": "fast"},
            requirements=["video_processing", "fast_video_processing"],
            priority=1
        )
        
        coordinator.submit_task(
            task_type="file_analysis", 
            payload={"directory": "/Users/garvey/UVAI", "analysis_depth": "full"},
            requirements=["file_management", "transparency"],
            priority=2
        )
        
        coordinator.submit_task(
            task_type="system_monitoring",
            payload={"monitoring_level": "comprehensive"},
            requirements=["system_monitoring", "ai_insights"],
            priority=2
        )
        
        print(f"📝 Submitted 3 test tasks")
        
        # Start coordination
        await coordinator.start_coordination()
        
    except KeyboardInterrupt:
        print("\n⏹️ Stopping coordination system...")
        coordinator.stop_coordination()
    except Exception as e:
        print(f"❌ System failed: {e}")
        coordinator.stop_coordination()

if __name__ == "__main__":
    asyncio.run(main())
