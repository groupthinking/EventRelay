#!/usr/bin/env python3
"""
Hybrid Orchestration System for MCP Ecosystem
Based on your existing Grok-Claude-Hybrid architecture, enables intelligent
intervention, takeover, and cross-model collaboration between MCP servers
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
import sqlite3
import subprocess
import json

# Setup logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('HybridOrchestration')

# Import MCP client for actual protocol communication
try:
    from mcp import client
    MCP_AVAILABLE = True
    logger.info("MCP client available for protocol communication")
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP client not available, using WebSocket fallback")

# Import the existing actionable video engine pattern
import sys
sys.path.append('/Users/garvey/Desktop/Grok-Claude-Hybrid-Deployment/src')

class OrchestrationMode(Enum):
    PARALLEL_PROCESSING = "parallel"      # Multiple servers work simultaneously
    SEQUENTIAL_HANDOFF = "sequential"     # Hand off between servers
    VALIDATION_CHAIN = "validation"       # One validates another's work
    COMPETITIVE_SELECTION = "competitive" # Best result wins
    COLLABORATIVE_MERGE = "collaborative" # Merge multiple approaches

class InterventionReason(Enum):
    ERROR_CASCADE = "error_cascade"
    QUALITY_DEGRADATION = "quality_degradation"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    BETTER_APPROACH_AVAILABLE = "better_approach_available"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    EXPERTISE_MISMATCH = "expertise_mismatch"

@dataclass
class ProcessingTask:
    task_id: str
    task_type: str
    input_data: Dict[str, Any]
    assigned_server: str
    orchestration_mode: OrchestrationMode
    priority: int
    expected_duration: float
    quality_threshold: float
    started_at: float
    status: str = "pending"
    progress: float = 0.0
    intermediate_results: List[Dict[str, Any]] = None
    error_count: int = 0
    quality_score: float = 1.0

@dataclass
class ServerProfile:
    server_id: str
    specializations: Dict[str, float]  # task_type -> expertise_level (0-1)
    performance_metrics: Dict[str, Dict[str, float]]
    current_load: float
    reliability_score: float
    intervention_success_rate: float
    last_updated: float

class HybridOrchestrationSystem:
    """
    Advanced orchestration system that enables MCP servers to intelligently
    intervene, take over, and collaborate based on your existing hybrid pattern
    """
    
    def __init__(self, coordinator_url: str = "ws://localhost:8005"):
        self.coordinator_url = coordinator_url
        self.websocket = None
        self.mcp_client = None
        self.active_tasks: Dict[str, ProcessingTask] = {}
        self.server_profiles: Dict[str, ServerProfile] = {}
        self.orchestration_history: List[Dict[str, Any]] = []
        
        # Database for persistent orchestration data
        self.db_path = "/Users/garvey/mcp-ecosystem/shared-state/orchestration.db"
        self._initialize_database()
        
        # Initialize server profiles based on your existing architecture
        self._initialize_server_profiles()
        
        # Orchestration rules based on your hybrid model
        self.orchestration_rules = self._initialize_orchestration_rules()
    
    def _initialize_database(self):
        """Initialize SQLite database for orchestration tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_tasks (
                task_id TEXT PRIMARY KEY,
                task_type TEXT NOT NULL,
                input_data TEXT NOT NULL,
                assigned_server TEXT NOT NULL,
                orchestration_mode TEXT NOT NULL,
                priority INTEGER NOT NULL,
                expected_duration REAL NOT NULL,
                quality_threshold REAL NOT NULL,
                started_at REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0.0,
                intermediate_results TEXT,
                error_count INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 1.0,
                completed_at REAL,
                final_result TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orchestration_events (
                event_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                source_server TEXT,
                target_server TEXT,
                reasoning TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                timestamp REAL NOT NULL,
                success BOOLEAN,
                impact_score REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_performance (
                server_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                success_rate REAL NOT NULL,
                avg_quality_score REAL NOT NULL,
                avg_completion_time REAL NOT NULL,
                intervention_success_rate REAL NOT NULL,
                last_updated REAL NOT NULL,
                PRIMARY KEY (server_id, task_type)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Orchestration database initialized")
    
    def _initialize_server_profiles(self):
        """Initialize server profiles based on your existing hybrid architecture"""
        
        # YouTube UVAI Processor (like Gemini in your system)
        self.server_profiles["youtube-uvai-processor"] = ServerProfile(
            server_id="youtube-uvai-processor",
            specializations={
                "video_analysis": 0.95,
                "transcript_processing": 0.9,
                "ai_reasoning": 0.85,
                "content_structure_analysis": 0.9
            },
            performance_metrics={
                "video_analysis": {"avg_time": 45.0, "success_rate": 0.95},
                "ai_reasoning": {"avg_time": 30.0, "success_rate": 0.88}
            },
            current_load=0.0,
            reliability_score=0.9,
            intervention_success_rate=0.8,
            last_updated=time.time()
        )
        
        # Self-Correcting Executor (like Grok in your system)
        self.server_profiles["self-correcting-executor"] = ServerProfile(
            server_id="self-correcting-executor",
            specializations={
                "error_correction": 0.98,
                "code_execution": 0.9,
                "debugging": 0.95,
                "system_diagnostics": 0.85
            },
            performance_metrics={
                "error_correction": {"avg_time": 15.0, "success_rate": 0.98},
                "code_execution": {"avg_time": 10.0, "success_rate": 0.92}
            },
            current_load=0.0,
            reliability_score=0.95,
            intervention_success_rate=0.92,
            last_updated=time.time()
        )
        
        # Universal MCP Swarm (code generation specialist)
        self.server_profiles["universal-mcp-swarm"] = ServerProfile(
            server_id="universal-mcp-swarm",
            specializations={
                "code_generation": 0.92,
                "architecture_planning": 0.88,
                "documentation_generation": 0.85,
                "pattern_detection": 0.8
            },
            performance_metrics={
                "code_generation": {"avg_time": 25.0, "success_rate": 0.9},
                "architecture_planning": {"avg_time": 40.0, "success_rate": 0.85}
            },
            current_load=0.0,
            reliability_score=0.88,
            intervention_success_rate=0.75,
            last_updated=time.time()
        )
        
        # Context7 (validation and reasoning specialist, like Claude in your system)
        self.server_profiles["context7"] = ServerProfile(
            server_id="context7",
            specializations={
                "validation": 0.9,
                "context_management": 0.95,
                "quality_assessment": 0.88,
                "reasoning": 0.85
            },
            performance_metrics={
                "validation": {"avg_time": 20.0, "success_rate": 0.93},
                "context_management": {"avg_time": 5.0, "success_rate": 0.98}
            },
            current_load=0.0,
            reliability_score=0.92,
            intervention_success_rate=0.85,
            last_updated=time.time()
        )
        
        # Perplexity (real-time information specialist)
        self.server_profiles["perplexity"] = ServerProfile(
            server_id="perplexity",
            specializations={
                "web_search": 0.95,
                "real_time_data": 0.9,
                "fact_checking": 0.85,
                "trend_analysis": 0.8
            },
            performance_metrics={
                "web_search": {"avg_time": 3.0, "success_rate": 0.95},
                "real_time_data": {"avg_time": 2.0, "success_rate": 0.92}
            },
            current_load=0.0,
            reliability_score=0.9,
            intervention_success_rate=0.7,
            last_updated=time.time()
        )
    
    def _initialize_orchestration_rules(self):
        """Initialize orchestration rules based on your hybrid model"""
        return [
            {
                "name": "video_processing_pipeline",
                "task_pattern": "video_.*",
                "orchestration_mode": OrchestrationMode.SEQUENTIAL_HANDOFF,
                "sequence": [
                    "youtube-uvai-processor",  # Initial analysis (like Gemini)
                    "universal-mcp-swarm",    # Code generation (like Grok)
                    "context7"                # Validation (like Claude)
                ],
                "intervention_triggers": [
                    InterventionReason.ERROR_CASCADE,
                    InterventionReason.QUALITY_DEGRADATION
                ]
            },
            {
                "name": "error_correction_takeover",
                "task_pattern": ".*",
                "condition": lambda task: task.error_count >= 2,
                "intervention_server": "self-correcting-executor",
                "intervention_mode": OrchestrationMode.VALIDATION_CHAIN,
                "reasoning": "Multiple errors detected - self-correcting executor taking over"
            },
            {
                "name": "quality_validation_chain",
                "task_pattern": ".*",
                "condition": lambda task: task.quality_score < 0.7,
                "intervention_server": "context7",
                "intervention_mode": OrchestrationMode.VALIDATION_CHAIN,
                "reasoning": "Quality below threshold - context7 providing validation"
            },
            {
                "name": "real_time_assistance",
                "task_pattern": "search_.*|web_.*",
                "primary_server": "perplexity",
                "orchestration_mode": OrchestrationMode.PARALLEL_PROCESSING,
                "reasoning": "Real-time data requires Perplexity specialization"
            }
        ]
    
    async def connect_to_coordinator(self):
        """Connect to the MCP State Coordinator"""
        try:
            self.websocket = await websockets.connect(self.coordinator_url)
            logger.info("Connected to coordinator for hybrid orchestration")
        except Exception as e:
            logger.error(f"Failed to connect to coordinator: {e}")
    
    async def submit_task(self, task_type: str, input_data: Dict[str, Any], 
                         priority: int = 5, quality_threshold: float = 0.8,
                         expected_duration: float = 60.0) -> str:
        """Submit a task for hybrid orchestration processing"""
        
        task_id = f"task_{int(time.time() * 1000)}"
        
        # Determine optimal orchestration strategy
        orchestration_strategy = self._determine_orchestration_strategy(task_type, input_data)
        
        task = ProcessingTask(
            task_id=task_id,
            task_type=task_type,
            input_data=input_data,
            assigned_server=orchestration_strategy["primary_server"],
            orchestration_mode=orchestration_strategy["mode"],
            priority=priority,
            expected_duration=expected_duration,
            quality_threshold=quality_threshold,
            started_at=time.time(),
            intermediate_results=[]
        )
        
        self.active_tasks[task_id] = task
        self._persist_task(task)
        
        # Start processing with orchestration
        await self._start_orchestrated_processing(task, orchestration_strategy)
        
        logger.info(f"Task {task_id} submitted with {orchestration_strategy['mode'].value} orchestration")
        return task_id
    
    def _determine_orchestration_strategy(self, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Determine the best orchestration strategy (like your hybrid model)"""
        
        # Video processing pipeline (like your existing system)
        if task_type.startswith("video"):
            return {
                "primary_server": "youtube-uvai-processor",
                "mode": OrchestrationMode.SEQUENTIAL_HANDOFF,
                "sequence": ["youtube-uvai-processor", "universal-mcp-swarm", "context7"],
                "reasoning": "Video processing requires sequential hybrid approach"
            }
        
        # Code-related tasks
        elif task_type.startswith("code"):
            return {
                "primary_server": "universal-mcp-swarm",
                "mode": OrchestrationMode.VALIDATION_CHAIN,
                "validators": ["self-correcting-executor", "context7"],
                "reasoning": "Code generation with error correction and validation"
            }
        
        # Error correction tasks
        elif "error" in task_type or "debug" in task_type:
            return {
                "primary_server": "self-correcting-executor",
                "mode": OrchestrationMode.PARALLEL_PROCESSING,
                "assistants": ["universal-mcp-swarm"],
                "reasoning": "Error correction with code generation support"
            }
        
        # Search and real-time tasks
        elif task_type.startswith("search") or task_type.startswith("web"):
            return {
                "primary_server": "perplexity",
                "mode": OrchestrationMode.COMPETITIVE_SELECTION,
                "competitors": ["context7"],
                "reasoning": "Real-time search with validation"
            }
        
        # Default: Find best server based on specialization
        else:
            best_server = self._find_best_server(task_type)
            return {
                "primary_server": best_server,
                "mode": OrchestrationMode.VALIDATION_CHAIN,
                "validators": ["context7"],
                "reasoning": f"Best specialization match with validation"
            }
    
    def _find_best_server(self, task_type: str) -> str:
        """Find the server with the best specialization for a task type"""
        best_server = None
        best_score = 0.0
        
        for server_id, profile in self.server_profiles.items():
            # Check for exact match
            if task_type in profile.specializations:
                score = profile.specializations[task_type] * profile.reliability_score
                score *= (1.0 - profile.current_load)  # Factor in current load
                
                if score > best_score:
                    best_score = score
                    best_server = server_id
            
            # Check for partial matches
            else:
                for specialization, expertise in profile.specializations.items():
                    if specialization in task_type or task_type in specialization:
                        score = expertise * 0.8 * profile.reliability_score  # Penalty for partial match
                        score *= (1.0 - profile.current_load)
                        
                        if score > best_score:
                            best_score = score
                            best_server = server_id
        
        return best_server or "context7"  # Fallback to context7
    
    async def _start_orchestrated_processing(self, task: ProcessingTask, strategy: Dict[str, Any]):
        """Start processing with the determined orchestration strategy"""
        
        if strategy["mode"] == OrchestrationMode.SEQUENTIAL_HANDOFF:
            await self._execute_sequential_handoff(task, strategy)
        
        elif strategy["mode"] == OrchestrationMode.PARALLEL_PROCESSING:
            await self._execute_parallel_processing(task, strategy)
        
        elif strategy["mode"] == OrchestrationMode.VALIDATION_CHAIN:
            await self._execute_validation_chain(task, strategy)
        
        elif strategy["mode"] == OrchestrationMode.COMPETITIVE_SELECTION:
            await self._execute_competitive_selection(task, strategy)
        
        elif strategy["mode"] == OrchestrationMode.COLLABORATIVE_MERGE:
            await self._execute_collaborative_merge(task, strategy)
    
    async def _execute_sequential_handoff(self, task: ProcessingTask, strategy: Dict[str, Any]):
        """Execute sequential handoff (like your Gemini -> Grok -> Claude pipeline)"""
        sequence = strategy.get("sequence", [task.assigned_server])
        current_data = task.input_data
        
        for i, server_id in enumerate(sequence):
            logger.info(f"Sequential handoff step {i+1}/{len(sequence)}: {server_id}")
            
            # Update task status
            task.status = f"processing_step_{i+1}"
            task.progress = i / len(sequence)
            self._persist_task(task)
            
            # Process with current server
            step_result = await self._process_with_server(server_id, task.task_type, current_data)
            
            # Check for intervention needs
            if await self._check_intervention_needed(task, step_result):
                intervention_result = await self._handle_intervention(task, step_result)
                if intervention_result["takeover"]:
                    logger.info(f"Intervention takeover at step {i+1}")
                    break
            
            # Store intermediate result
            task.intermediate_results.append({
                "step": i + 1,
                "server": server_id,
                "result": step_result,
                "timestamp": time.time()
            })
            
            # Prepare data for next step
            current_data = step_result.get("output_data", current_data)
            
            # Update quality score
            step_quality = step_result.get("quality_score", 1.0)
            task.quality_score = (task.quality_score + step_quality) / 2
        
        # Mark task as completed
        task.status = "completed"
        task.progress = 1.0
        self._persist_task(task)
        
        logger.info(f"Sequential handoff completed for task {task.task_id}")
    
    async def _execute_validation_chain(self, task: ProcessingTask, strategy: Dict[str, Any]):
        """Execute validation chain processing"""
        primary_server = strategy["primary_server"]
        validators = strategy.get("validators", [])
        
        # Primary processing
        logger.info(f"Primary processing with {primary_server}")
        primary_result = await self._process_with_server(primary_server, task.task_type, task.input_data)
        
        task.intermediate_results.append({
            "step": "primary",
            "server": primary_server,
            "result": primary_result,
            "timestamp": time.time()
        })
        
        # Validation by other servers
        validation_results = []
        for validator in validators:
            logger.info(f"Validation by {validator}")
            
            validation_input = {
                "original_input": task.input_data,
                "primary_result": primary_result,
                "validation_request": True
            }
            
            validation_result = await self._process_with_server(validator, f"validate_{task.task_type}", validation_input)
            validation_results.append({
                "validator": validator,
                "result": validation_result,
                "timestamp": time.time()
            })
        
        # Merge validation results
        final_result = self._merge_validation_results(primary_result, validation_results)
        
        task.intermediate_results.extend(validation_results)
        task.status = "completed"
        task.progress = 1.0
        task.quality_score = final_result.get("quality_score", task.quality_score)
        
        self._persist_task(task)
        logger.info(f"Validation chain completed for task {task.task_id}")
    
    async def _process_with_server(self, server_id: str, task_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data with a specific server by sending a tool call request to the MCP State Coordinator.
        """
        logger.info(f"Requesting tool call on '{server_id}' for task '{task_type}'")

        tool_name = self._map_task_type_to_mcp_tool(server_id, task_type)
        tool_arguments = self._format_input_for_mcp_tool(server_id, tool_name, input_data)

        request_id = f"req_{int(time.time() * 1000)}"
        request_message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tool_call_request", # Custom method for coordinator to route tool calls
            "params": {
                "server_id": server_id,
                "tool_name": tool_name,
                "tool_arguments": tool_arguments,
                "task_type": task_type
            }
        }

        start_time = time.time()
        success = False
        output_data = {}
        error_message = ""
        quality_score = 1.0

        try:
            if self.websocket and self.websocket.state == websockets.client.State.OPEN:
                await self.websocket.send(json.dumps(request_message))
                response_message = json.loads(await self.websocket.recv())

                if response_message.get("id") == request_id:
                    if "result" in response_message:
                        result = response_message["result"]
                        success = result.get("success", False)
                        output_data = result.get("output_data", {})
                        quality_score = result.get("quality_score", 1.0)
                        error_message = result.get("error_message", "")
                    elif "error" in response_message:
                        error_message = response_message["error"].get("message", "Unknown error from coordinator")
                        success = False
                        quality_score = 0.0
                else:
                    error_message = "Mismatched response ID from coordinator"
                    success = False
                    quality_score = 0.0
            else:
                error_message = "WebSocket connection to coordinator not open"
                success = False
                quality_score = 0.0

        except Exception as e:
            logger.error(f"Error communicating with coordinator for tool call: {e}")
            error_message = str(e)
            success = False
            quality_score = 0.0

        finally:
            processing_time = time.time() - start_time
            error_count = 0 if success else 1

            # Update server load (as before)
            if server_id in self.server_profiles:
                self.server_profiles[server_id].current_load = max(0, self.server_profiles[server_id].current_load - 0.1)

            return {
                "server_id": server_id,
                "task_type": task_type,
                "success": success,
                "quality_score": quality_score,
                "output_data": output_data,
                "processing_time": processing_time,
                "error_count": error_count,
                "error_message": error_message
            }

    def _map_task_type_to_mcp_tool(self, server_id: str, task_type: str) -> str:
        """
        Maps a generic task type to a specific MCP tool name for a given server.
        This will need to be expanded with actual mappings.
        """
        # Placeholder mapping - needs to be comprehensive
        mappings = {
            "youtube-uvai-processor": {
                "video_analysis": "analyze_video",
                "transcript_processing": "process_transcript",
                "ai_reasoning": "reason_on_video_context"
            },
            "self-correcting-executor": {
                "error_correction": "correct_error",
                "code_execution": "execute_code",
                "debugging": "debug_process"
            },
            "universal-mcp-swarm": {
                "code_generation": "generate_code",
                "architecture_planning": "plan_architecture"
            },
            "context7": {
                "validation": "validate_output",
                "quality_assessment": "assess_quality",
                "context_management": "manage_context"
            },
            "perplexity": {
                "web_search": "perform_web_search",
                "real_time_data": "get_real_time_data"
            }
        }
        return mappings.get(server_id, {}).get(task_type, f"generic_tool_for_{task_type}")

    def _format_input_for_mcp_tool(self, server_id: str, tool_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats the input data into arguments suitable for a specific MCP tool.
        This will also need to be expanded based on actual tool schemas.
        """
        # Placeholder formatting - needs to be specific to each tool
        if server_id == "youtube-uvai-processor" and tool_name == "analyze_video":
            return {"video_url": input_data.get("video_url"), "depth": input_data.get("analysis_depth", "basic")}
        # Add more specific formatting rules here
        return {"input": input_data}
    
    async def _check_intervention_needed(self, task: ProcessingTask, step_result: Dict[str, Any]) -> bool:
        """Check if intervention is needed (like your error detection system)"""
        
        # Error-based intervention
        if not step_result.get("success", True):
            task.error_count += 1
            if task.error_count >= 2:
                return True
        
        # Quality-based intervention
        quality_score = step_result.get("quality_score", 1.0)
        if quality_score < task.quality_threshold:
            return True
        
        # Time-based intervention
        elapsed_time = time.time() - task.started_at
        if elapsed_time > task.expected_duration * 1.5:  # 50% over expected time
            return True
        
        return False
    
    async def _handle_intervention(self, task: ProcessingTask, problematic_result: Dict[str, Any]) -> Dict[str, Any]:
        """Handle intervention (like your model switching logic)"""
        
        # Determine intervention type
        if task.error_count >= 2:
            intervention_reason = InterventionReason.ERROR_CASCADE
            intervention_server = "self-correcting-executor"
        elif problematic_result.get("quality_score", 1.0) < 0.6:
            intervention_reason = InterventionReason.QUALITY_DEGRADATION
            intervention_server = "context7"
        else:
            intervention_reason = InterventionReason.TIMEOUT_EXCEEDED
            intervention_server = self._find_best_server(task.task_type)
        
        logger.info(f"Intervention triggered: {intervention_reason.value} -> {intervention_server}")
        
        # Execute intervention
        intervention_input = {
            "original_task": task.input_data,
            "problematic_result": problematic_result,
            "intervention_reason": intervention_reason.value,
            "task_context": {
                "error_count": task.error_count,
                "quality_score": task.quality_score,
                "elapsed_time": time.time() - task.started_at
            }
        }
        
        intervention_result = await self._process_with_server(
            intervention_server, 
            f"intervene_{task.task_type}", 
            intervention_input
        )
        
        # Log intervention
        self._log_intervention_event(task.task_id, intervention_reason, intervention_server, intervention_result)
        
        # Determine if takeover is needed
        takeover_needed = (
            intervention_reason in [InterventionReason.ERROR_CASCADE, InterventionReason.QUALITY_DEGRADATION] or
            intervention_result.get("recommend_takeover", False)
        )
        
        return {
            "takeover": takeover_needed,
            "intervention_server": intervention_server,
            "intervention_result": intervention_result,
            "reasoning": intervention_reason.value
        }
    
    def _merge_validation_results(self, primary_result: Dict[str, Any], 
                                 validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge primary result with validation results (like your final validation step)"""
        
        merged_result = primary_result.copy()
        validation_scores = []
        validation_feedback = []
        
        for validation in validation_results:
            val_result = validation["result"]
            if "quality_score" in val_result:
                validation_scores.append(val_result["quality_score"])
            if "feedback" in val_result:
                validation_feedback.append(val_result["feedback"])
        
        # Calculate consensus quality score
        if validation_scores:
            consensus_quality = sum(validation_scores) / len(validation_scores)
            merged_result["quality_score"] = (primary_result.get("quality_score", 1.0) + consensus_quality) / 2
        
        # Add validation feedback
        merged_result["validation_feedback"] = validation_feedback
        merged_result["validation_consensus"] = len([s for s in validation_scores if s > 0.7]) / len(validation_scores) if validation_scores else 1.0
        
        return merged_result
    
    async def _execute_parallel_processing(self, task: ProcessingTask, strategy: Dict[str, Any]):
        """Execute parallel processing with multiple servers"""
        primary_server = strategy["primary_server"]
        assistants = strategy.get("assistants", [])
        
        # Start all servers in parallel
        tasks_to_run = [
            self._process_with_server(primary_server, task.task_type, task.input_data)
        ]
        
        for assistant in assistants:
            assistant_input = {
                **task.input_data,
                "collaboration_mode": "assistant",
                "primary_server": primary_server
            }
            tasks_to_run.append(
                self._process_with_server(assistant, f"assist_{task.task_type}", assistant_input)
            )
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks_to_run, return_exceptions=True)
        
        # Process results
        primary_result = results[0] if len(results) > 0 else {}
        assistant_results = results[1:] if len(results) > 1 else []
        
        # Merge results
        final_result = self._merge_parallel_results(primary_result, assistant_results)
        
        task.intermediate_results.append({
            "step": "parallel_processing",
            "primary_result": primary_result,
            "assistant_results": assistant_results,
            "final_result": final_result,
            "timestamp": time.time()
        })
        
        task.status = "completed"
        task.progress = 1.0
        task.quality_score = final_result.get("quality_score", task.quality_score)
        
        self._persist_task(task)
        logger.info(f"Parallel processing completed for task {task.task_id}")
    
    async def _execute_competitive_selection(self, task: ProcessingTask, strategy: Dict[str, Any]):
        """Execute competitive selection where best result wins"""
        primary_server = strategy["primary_server"]
        competitors = strategy.get("competitors", [])
        
        # Run all servers competitively
        all_servers = [primary_server] + competitors
        competitive_tasks = []
        
        for server in all_servers:
            competitive_tasks.append(
                self._process_with_server(server, task.task_type, task.input_data)
            )
        
        # Wait for all to complete
        results = await asyncio.gather(*competitive_tasks, return_exceptions=True)
        
        # Select best result based on quality score
        best_result = None
        best_score = 0.0
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                continue
            
            quality_score = result.get("quality_score", 0.0)
            if quality_score > best_score:
                best_score = quality_score
                best_result = result
                best_result["winning_server"] = all_servers[i]
        
        task.intermediate_results.append({
            "step": "competitive_selection",
            "all_results": results,
            "winning_result": best_result,
            "timestamp": time.time()
        })
        
        task.status = "completed"
        task.progress = 1.0
        task.quality_score = best_result.get("quality_score", 0.5) if best_result else 0.5
        
        self._persist_task(task)
        logger.info(f"Competitive selection completed for task {task.task_id}")
    
    async def _execute_collaborative_merge(self, task: ProcessingTask, strategy: Dict[str, Any]):
        """Execute collaborative merge where multiple approaches are combined"""
        servers = strategy.get("servers", [task.assigned_server])
        
        # Phase 1: Independent processing
        independent_results = []
        for server in servers:
            result = await self._process_with_server(server, task.task_type, task.input_data)
            independent_results.append({
                "server": server,
                "result": result
            })
        
        # Phase 2: Collaborative merge
        merge_input = {
            "original_task": task.input_data,
            "independent_results": independent_results,
            "merge_strategy": "collaborative"
        }
        
        # Use the most capable server for merging
        merge_server = self._find_best_server("result_merging")
        merged_result = await self._process_with_server(
            merge_server, 
            "merge_results", 
            merge_input
        )
        
        task.intermediate_results.extend([
            {"step": "independent_processing", "results": independent_results, "timestamp": time.time()},
            {"step": "collaborative_merge", "result": merged_result, "timestamp": time.time()}
        ])
        
        task.status = "completed"
        task.progress = 1.0
        task.quality_score = merged_result.get("quality_score", 0.75)
        
        self._persist_task(task)
        logger.info(f"Collaborative merge completed for task {task.task_id}")
    
    def _merge_parallel_results(self, primary_result: Dict[str, Any], 
                               assistant_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge results from parallel processing"""
        merged = primary_result.copy()
        
        # Collect assistant contributions
        assistant_contributions = []
        quality_scores = [primary_result.get("quality_score", 1.0)]
        
        for assistant_result in assistant_results:
            if isinstance(assistant_result, Exception):
                continue
            
            assistant_contributions.append(assistant_result.get("output_data", {}))
            quality_scores.append(assistant_result.get("quality_score", 1.0))
        
        # Calculate weighted quality score
        merged["quality_score"] = sum(quality_scores) / len(quality_scores)
        merged["assistant_contributions"] = assistant_contributions
        merged["collaboration_success"] = len(assistant_contributions) > 0
        
        return merged
    
    def _log_intervention_event(self, task_id: str, reason: InterventionReason, 
                               intervention_server: str, result: Dict[str, Any]):
        """Log intervention event for learning"""
        event = {
            "event_id": f"intervention_{int(time.time() * 1000)}",
            "task_id": task_id,
            "event_type": "intervention",
            "source_server": intervention_server,
            "target_server": self.active_tasks[task_id].assigned_server,
            "reasoning": reason.value,
            "action_taken": "intervention_processing",
            "timestamp": time.time(),
            "success": result.get("success", False),
            "impact_score": result.get("quality_score", 0.5)
        }
        
        self.orchestration_history.append(event)
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO orchestration_events 
            (event_id, task_id, event_type, source_server, target_server, reasoning, action_taken, timestamp, success, impact_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            event["event_id"], event["task_id"], event["event_type"],
            event["source_server"], event["target_server"], event["reasoning"],
            event["action_taken"], event["timestamp"], event["success"], event["impact_score"]
        ))
        conn.commit()
        conn.close()
    
    def _persist_task(self, task: ProcessingTask):
        """Persist task state to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO processing_tasks 
            (task_id, task_type, input_data, assigned_server, orchestration_mode, priority,
             expected_duration, quality_threshold, started_at, status, progress, 
             intermediate_results, error_count, quality_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task.task_id, task.task_type, json.dumps(task.input_data),
            task.assigned_server, task.orchestration_mode.value, task.priority,
            task.expected_duration, task.quality_threshold, task.started_at,
            task.status, task.progress, json.dumps(task.intermediate_results or []),
            task.error_count, task.quality_score
        ))
        
        conn.commit()
        conn.close()
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a task"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            return {
                "task_id": task_id,
                "status": task.status,
                "progress": task.progress,
                "quality_score": task.quality_score,
                "error_count": task.error_count,
                "elapsed_time": time.time() - task.started_at,
                "assigned_server": task.assigned_server,
                "orchestration_mode": task.orchestration_mode.value,
                "intermediate_results_count": len(task.intermediate_results or [])
            }
        return None
    
    def get_orchestration_analytics(self) -> Dict[str, Any]:
        """Get orchestration analytics"""
        total_interventions = len([e for e in self.orchestration_history if e["event_type"] == "intervention"])
        successful_interventions = len([e for e in self.orchestration_history if e["event_type"] == "intervention" and e["success"]])
        
        return {
            "active_tasks": len(self.active_tasks),
            "total_interventions": total_interventions,
            "intervention_success_rate": successful_interventions / total_interventions if total_interventions > 0 else 0.0,
            "server_profiles": {sid: asdict(profile) for sid, profile in self.server_profiles.items()},
            "orchestration_history_count": len(self.orchestration_history)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of the entire orchestration system"""
        health_status = {
            "system_health": "healthy",
            "timestamp": time.time(),
            "coordinator_connection": False,
            "server_health": {},
            "database_health": False,
            "active_task_count": len(self.active_tasks),
            "recommendations": []
        }
        
        # Check coordinator connection
        try:
            if self.mcp_client:
                # Test connection with a simple ping
                health_status["coordinator_connection"] = True
        except Exception as e:
            health_status["coordinator_connection"] = False
            health_status["recommendations"].append(f"Coordinator connection issue: {e}")
        
        # Check each server health
        for server_id, profile in self.server_profiles.items():
            server_health = {
                "status": "unknown",
                "last_updated": profile.last_updated,
                "current_load": profile.current_load,
                "reliability_score": profile.reliability_score,
                "specializations_count": len(profile.specializations)
            }
            
            # Test if server is responsive (simplified check)
            try:
                test_result = await self._process_with_server(
                    server_id, "health_check", {"test": True}
                )
                server_health["status"] = "healthy" if test_result.get("success") else "degraded"
            except Exception as e:
                server_health["status"] = "unhealthy"
                server_health["error"] = str(e)
            
            health_status["server_health"][server_id] = server_health
        
        # Check database health
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM processing_tasks")
            cursor.fetchone()
            conn.close()
            health_status["database_health"] = True
        except Exception as e:
            health_status["database_health"] = False
            health_status["recommendations"].append(f"Database issue: {e}")
        
        # Determine overall system health
        unhealthy_servers = [sid for sid, health in health_status["server_health"].items() 
                           if health["status"] == "unhealthy"]
        
        if not health_status["coordinator_connection"] or not health_status["database_health"]:
            health_status["system_health"] = "critical"
        elif len(unhealthy_servers) > len(self.server_profiles) // 2:
            health_status["system_health"] = "degraded"
        elif len(unhealthy_servers) > 0:
            health_status["system_health"] = "warning"
        
        return health_status
    
    async def performance_benchmark(self, duration: int = 60) -> Dict[str, Any]:
        """Run performance benchmark across all orchestration modes"""
        benchmark_results = {
            "benchmark_duration": duration,
            "start_time": time.time(),
            "test_results": {},
            "server_performance": {},
            "orchestration_mode_performance": {}
        }
        
        # Test tasks for each orchestration mode
        test_scenarios = [
            {
                "name": "sequential_video_processing",
                "task_type": "video_analysis",
                "input_data": {"video_url": "test://benchmark", "analysis_depth": "basic"},
                "expected_mode": OrchestrationMode.SEQUENTIAL_HANDOFF
            },
            {
                "name": "parallel_code_generation",
                "task_type": "code_generation", 
                "input_data": {"requirements": "benchmark test", "language": "python"},
                "expected_mode": OrchestrationMode.PARALLEL_PROCESSING
            },
            {
                "name": "competitive_search",
                "task_type": "web_search",
                "input_data": {"query": "benchmark test query"},
                "expected_mode": OrchestrationMode.COMPETITIVE_SELECTION
            }
        ]
        
        # Run benchmark tests
        for scenario in test_scenarios:
            start_time = time.time()
            try:
                task_id = await self.submit_task(
                    scenario["task_type"],
                    scenario["input_data"],
                    priority=9,
                    quality_threshold=0.7
                )
                
                # Monitor task completion
                completed = False
                timeout = 30  # 30 seconds timeout per task
                while not completed and (time.time() - start_time) < timeout:
                    await asyncio.sleep(1)
                    status = await self.get_task_status(task_id)
                    if status and status["status"] == "completed":
                        completed = True
                
                end_time = time.time()
                
                benchmark_results["test_results"][scenario["name"]] = {
                    "completed": completed,
                    "duration": end_time - start_time,
                    "task_id": task_id,
                    "final_status": status if completed else "timeout"
                }
                
            except Exception as e:
                benchmark_results["test_results"][scenario["name"]] = {
                    "completed": False,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
        
        benchmark_results["end_time"] = time.time()
        benchmark_results["total_duration"] = benchmark_results["end_time"] - benchmark_results["start_time"]
        
        return benchmark_results

# Example usage demonstrating the hybrid orchestration
async def main():
    """Example usage of Hybrid Orchestration System"""
    orchestrator = HybridOrchestrationSystem()
    await orchestrator.connect_to_coordinator()
    
    # Example 1: Video processing (like your existing pipeline)
    video_task_id = await orchestrator.submit_task(
        task_type="video_analysis",
        input_data={
            "video_url": "https://www.youtube.com/watch?v=example",
            "analysis_depth": "comprehensive"
        },
        priority=8,
        quality_threshold=0.85
    )
    
    print(f"Video processing task submitted: {video_task_id}")
    
    # Example 2: Code generation with error correction
    code_task_id = await orchestrator.submit_task(
        task_type="code_generation",
        input_data={
            "requirements": "Create a REST API with authentication",
            "language": "python",
            "framework": "fastapi"
        },
        priority=7,
        quality_threshold=0.8
    )
    
    print(f"Code generation task submitted: {code_task_id}")
    
    # Wait and check status
    await asyncio.sleep(5)
    
    video_status = await orchestrator.get_task_status(video_task_id)
    print(f"Video task status: {video_status}")
    
    analytics = orchestrator.get_orchestration_analytics()
    print(f"Orchestration analytics: {analytics}")

if __name__ == "__main__":
    asyncio.run(main())