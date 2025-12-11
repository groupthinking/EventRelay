#!/usr/bin/env python3
"""
Intelligent Intervention System
Enables MCP servers to monitor, intervene, and take over each other's processes
when errors occur or better approaches are identified
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
import sqlite3
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('IntelligentIntervention')

class InterventionTrigger(Enum):
    ERROR_DETECTED = "error_detected"
    INEFFICIENT_APPROACH = "inefficient_approach"
    BETTER_CAPABILITY_AVAILABLE = "better_capability_available"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    QUALITY_THRESHOLD_FAILED = "quality_threshold_failed"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SECURITY_CONCERN = "security_concern"

class InterventionType(Enum):
    GUIDANCE = "guidance"          # Provide suggestions without taking over
    ASSISTANCE = "assistance"      # Work alongside the current server
    TAKEOVER = "takeover"         # Complete takeover of the process
    CORRECTION = "correction"      # Fix specific errors and hand back control
    OPTIMIZATION = "optimization" # Improve the current approach

@dataclass
class ProcessMonitor:
    process_id: str
    server_id: str
    task_type: str
    started_at: float
    last_update: float
    status: str
    progress_indicators: Dict[str, Any]
    error_count: int = 0
    quality_score: float = 1.0
    resource_usage: Dict[str, float] = None
    expected_completion: Optional[float] = None

@dataclass
class InterventionEvent:
    intervention_id: str
    trigger: InterventionTrigger
    intervention_type: InterventionType
    source_server: str      # Server detecting the issue
    target_server: str      # Server being monitored
    target_process: str     # Process being monitored
    confidence: float       # Confidence in the intervention decision
    reasoning: str          # Why this intervention is needed
    proposed_action: Dict[str, Any]
    timestamp: float
    status: str = "pending" # pending, accepted, rejected, completed

class IntelligentInterventionSystem:
    """Core system for managing intelligent interventions between MCP servers"""
    
    def __init__(self, coordinator_url: str = "ws://localhost:8005"):
        self.coordinator_url = coordinator_url
        self.websocket = None
        self.active_monitors: Dict[str, ProcessMonitor] = {}
        self.intervention_history: List[InterventionEvent] = []
        self.server_capabilities: Dict[str, Dict[str, Any]] = {}
        self.intervention_rules: List[Dict[str, Any]] = []
        self.quality_thresholds: Dict[str, float] = {}
        
        # Database for persistent intervention tracking
        self.db_path = "/Users/garvey/mcp-ecosystem/shared-state/interventions.db"
        self._initialize_database()
        self._initialize_intervention_rules()
    
    def _initialize_database(self):
        """Initialize SQLite database for intervention tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_monitors (
                process_id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                started_at REAL NOT NULL,
                last_update REAL NOT NULL,
                status TEXT NOT NULL,
                progress_indicators TEXT,
                error_count INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 1.0,
                resource_usage TEXT,
                expected_completion REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interventions (
                intervention_id TEXT PRIMARY KEY,
                trigger_type TEXT NOT NULL,
                intervention_type TEXT NOT NULL,
                source_server TEXT NOT NULL,
                target_server TEXT NOT NULL,
                target_process TEXT NOT NULL,
                confidence REAL NOT NULL,
                reasoning TEXT NOT NULL,
                proposed_action TEXT NOT NULL,
                timestamp REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                outcome TEXT,
                effectiveness_score REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_capabilities (
                server_id TEXT PRIMARY KEY,
                capabilities TEXT NOT NULL,
                specializations TEXT,
                performance_metrics TEXT,
                reliability_score REAL DEFAULT 1.0,
                last_updated REAL NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Intervention database initialized")
    
    def _initialize_intervention_rules(self):
        """Initialize intelligent intervention rules"""
        self.intervention_rules = [
            {
                "name": "error_cascade_prevention",
                "trigger": InterventionTrigger.ERROR_DETECTED,
                "condition": lambda monitor: monitor.error_count >= 3,
                "intervention_type": InterventionType.TAKEOVER,
                "priority": 9,
                "reasoning": "Multiple errors detected - preventing cascade failure"
            },
            {
                "name": "timeout_intervention",
                "trigger": InterventionTrigger.TIMEOUT_EXCEEDED,
                "condition": lambda monitor: (
                    monitor.expected_completion and 
                    time.time() > monitor.expected_completion + 300  # 5 minutes grace
                ),
                "intervention_type": InterventionType.ASSISTANCE,
                "priority": 8,
                "reasoning": "Process exceeded expected completion time"
            },
            {
                "name": "quality_degradation",
                "trigger": InterventionTrigger.QUALITY_THRESHOLD_FAILED,
                "condition": lambda monitor: monitor.quality_score < 0.6,
                "intervention_type": InterventionType.OPTIMIZATION,
                "priority": 7,
                "reasoning": "Output quality below acceptable threshold"
            },
            {
                "name": "better_capability_available",
                "trigger": InterventionTrigger.BETTER_CAPABILITY_AVAILABLE,
                "condition": self._check_better_capability_available,
                "intervention_type": InterventionType.GUIDANCE,
                "priority": 6,
                "reasoning": "Server with superior capability available for this task"
            },
            {
                "name": "resource_exhaustion",
                "trigger": InterventionTrigger.RESOURCE_EXHAUSTION,
                "condition": lambda monitor: (
                    monitor.resource_usage and 
                    monitor.resource_usage.get('memory_percent', 0) > 90
                ),
                "intervention_type": InterventionType.TAKEOVER,
                "priority": 8,
                "reasoning": "Resource exhaustion detected"
            }
        ]
        
        # Quality thresholds by task type
        self.quality_thresholds = {
            'video_analysis': 0.8,
            'code_generation': 0.7,
            'error_correction': 0.9,
            'context_management': 0.8,
            'web_search': 0.75
        }
    
    async def connect_to_coordinator(self):
        """Connect to the MCP State Coordinator"""
        try:
            self.websocket = await websockets.connect(self.coordinator_url)
            logger.info(f"Connected to coordinator for intervention monitoring")
        except Exception as e:
            logger.error(f"Failed to connect to coordinator: {e}")
    
    def register_server_capabilities(self, server_id: str, capabilities: Dict[str, Any]):
        """Register server capabilities for intelligent routing decisions"""
        self.server_capabilities[server_id] = {
            'capabilities': capabilities.get('capabilities', []),
            'specializations': capabilities.get('specializations', {}),
            'performance_metrics': capabilities.get('performance_metrics', {}),
            'reliability_score': capabilities.get('reliability_score', 1.0),
            'last_updated': time.time()
        }
        
        # Persist to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO server_capabilities 
            (server_id, capabilities, specializations, performance_metrics, reliability_score, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            server_id,
            json.dumps(capabilities.get('capabilities', [])),
            json.dumps(capabilities.get('specializations', {})),
            json.dumps(capabilities.get('performance_metrics', {})),
            capabilities.get('reliability_score', 1.0),
            time.time()
        ))
        conn.commit()
        conn.close()
        
        logger.info(f"Registered capabilities for server: {server_id}")
    
    def start_process_monitoring(self, process_id: str, server_id: str, task_type: str, 
                                expected_duration: Optional[float] = None) -> ProcessMonitor:
        """Start monitoring a process for potential intervention needs"""
        monitor = ProcessMonitor(
            process_id=process_id,
            server_id=server_id,
            task_type=task_type,
            started_at=time.time(),
            last_update=time.time(),
            status="running",
            progress_indicators={},
            expected_completion=time.time() + expected_duration if expected_duration else None
        )
        
        self.active_monitors[process_id] = monitor
        
        # Persist to database
        self._persist_monitor(monitor)
        
        logger.info(f"Started monitoring process {process_id} on server {server_id}")
        return monitor
    
    def update_process_status(self, process_id: str, status_update: Dict[str, Any]):
        """Update process status and check for intervention triggers"""
        if process_id not in self.active_monitors:
            logger.warning(f"Process {process_id} not found in active monitors")
            return
        
        monitor = self.active_monitors[process_id]
        monitor.last_update = time.time()
        
        # Update various status indicators
        if 'status' in status_update:
            monitor.status = status_update['status']
        
        if 'error_count' in status_update:
            monitor.error_count = status_update['error_count']
        
        if 'quality_score' in status_update:
            monitor.quality_score = status_update['quality_score']
        
        if 'progress_indicators' in status_update:
            monitor.progress_indicators.update(status_update['progress_indicators'])
        
        if 'resource_usage' in status_update:
            monitor.resource_usage = status_update['resource_usage']
        
        # Check for intervention triggers
        asyncio.create_task(self._check_intervention_triggers(monitor))
        
        # Persist updates
        self._persist_monitor(monitor)
    
    async def _check_intervention_triggers(self, monitor: ProcessMonitor):
        """Check if any intervention rules are triggered"""
        for rule in self.intervention_rules:
            try:
                if rule['condition'](monitor):
                    await self._trigger_intervention(monitor, rule)
            except Exception as e:
                logger.error(f"Error checking intervention rule {rule['name']}: {e}")
    
    async def _trigger_intervention(self, monitor: ProcessMonitor, rule: Dict[str, Any]):
        """Trigger an intervention based on a rule"""
        
        # Find the best server to handle the intervention
        best_server = self._find_best_intervention_server(monitor, rule)
        
        if not best_server:
            logger.warning(f"No suitable server found for intervention on {monitor.process_id}")
            return
        
        intervention = InterventionEvent(
            intervention_id=f"intervention_{int(time.time() * 1000)}",
            trigger=rule['trigger'],
            intervention_type=rule['intervention_type'],
            source_server=best_server,
            target_server=monitor.server_id,
            target_process=monitor.process_id,
            confidence=self._calculate_intervention_confidence(monitor, rule, best_server),
            reasoning=rule['reasoning'],
            proposed_action=self._generate_intervention_action(monitor, rule, best_server),
            timestamp=time.time()
        )
        
        # Only proceed if confidence is high enough
        if intervention.confidence >= 0.7:
            await self._execute_intervention(intervention)
        else:
            logger.info(f"Intervention confidence too low ({intervention.confidence:.2f}) for {monitor.process_id}")
    
    def _find_best_intervention_server(self, monitor: ProcessMonitor, rule: Dict[str, Any]) -> Optional[str]:
        """Find the best server to handle the intervention"""
        task_type = monitor.task_type
        intervention_type = rule['intervention_type']
        
        # Score servers based on their suitability
        server_scores = {}
        
        for server_id, capabilities in self.server_capabilities.items():
            if server_id == monitor.server_id:  # Don't intervene with self
                continue
            
            score = 0.0
            
            # Base capability match
            server_capabilities = capabilities.get('capabilities', [])
            if task_type in server_capabilities:
                score += 3.0
            
            # Specialization bonus
            specializations = capabilities.get('specializations', {})
            if task_type in specializations:
                specialization_score = specializations[task_type]
                score += specialization_score * 2.0
            
            # Reliability factor
            reliability = capabilities.get('reliability_score', 1.0)
            score *= reliability
            
            # Performance metrics
            performance = capabilities.get('performance_metrics', {})
            task_performance = performance.get(task_type, {})
            if 'success_rate' in task_performance:
                score *= task_performance['success_rate']
            
            # Intervention type suitability
            if intervention_type == InterventionType.TAKEOVER:
                # For takeovers, prioritize servers with high capability
                if 'error_correction' in server_capabilities:
                    score += 2.0
            elif intervention_type == InterventionType.OPTIMIZATION:
                # For optimization, prioritize specialized servers
                if task_type in specializations:
                    score += 1.5
            
            server_scores[server_id] = score
        
        # Return the highest scoring server
        if server_scores:
            best_server = max(server_scores.items(), key=lambda x: x[1])
            if best_server[1] > 2.0:  # Minimum threshold
                return best_server[0]
        
        return None
    
    def _calculate_intervention_confidence(self, monitor: ProcessMonitor, rule: Dict[str, Any], 
                                         intervention_server: str) -> float:
        """Calculate confidence level for the intervention"""
        confidence = 0.5  # Base confidence
        
        # Rule priority factor
        rule_priority = rule.get('priority', 5)
        confidence += (rule_priority / 10.0) * 0.3
        
        # Server capability factor
        if intervention_server in self.server_capabilities:
            server_caps = self.server_capabilities[intervention_server]
            reliability = server_caps.get('reliability_score', 1.0)
            confidence += reliability * 0.2
            
            # Task-specific performance
            performance = server_caps.get('performance_metrics', {})
            task_performance = performance.get(monitor.task_type, {})
            if 'success_rate' in task_performance:
                confidence += task_performance['success_rate'] * 0.2
        
        # Urgency factor
        if rule['trigger'] in [InterventionTrigger.ERROR_DETECTED, InterventionTrigger.RESOURCE_EXHAUSTION]:
            confidence += 0.2
        
        # Historical success factor
        historical_success = self._get_historical_intervention_success(
            rule['intervention_type'], monitor.task_type, intervention_server
        )
        confidence += historical_success * 0.1
        
        return min(confidence, 1.0)
    
    def _generate_intervention_action(self, monitor: ProcessMonitor, rule: Dict[str, Any], 
                                    intervention_server: str) -> Dict[str, Any]:
        """Generate the specific action to take for the intervention"""
        action = {
            'intervention_server': intervention_server,
            'original_server': monitor.server_id,
            'process_id': monitor.process_id,
            'task_type': monitor.task_type,
            'intervention_method': rule['intervention_type'].value
        }
        
        if rule['intervention_type'] == InterventionType.TAKEOVER:
            action.update({
                'action': 'complete_takeover',
                'preserve_context': True,
                'notify_original_server': True,
                'handback_conditions': ['task_completion', 'error_resolution']
            })
        
        elif rule['intervention_type'] == InterventionType.ASSISTANCE:
            action.update({
                'action': 'provide_assistance',
                'collaboration_mode': 'parallel_processing',
                'coordination_required': True
            })
        
        elif rule['intervention_type'] == InterventionType.GUIDANCE:
            action.update({
                'action': 'provide_guidance',
                'guidance_type': 'suggestions',
                'maintain_control': True
            })
        
        elif rule['intervention_type'] == InterventionType.CORRECTION:
            action.update({
                'action': 'error_correction',
                'correction_scope': 'specific_errors',
                'return_control': True
            })
        
        elif rule['intervention_type'] == InterventionType.OPTIMIZATION:
            action.update({
                'action': 'optimize_approach',
                'optimization_areas': ['performance', 'quality', 'efficiency'],
                'collaborative': True
            })
        
        # Add context preservation
        action['context_data'] = {
            'current_progress': monitor.progress_indicators,
            'error_history': monitor.error_count,
            'quality_metrics': monitor.quality_score,
            'time_elapsed': time.time() - monitor.started_at
        }
        
        return action
    
    async def _execute_intervention(self, intervention: InterventionEvent):
        """Execute the intervention"""
        logger.info(f"Executing intervention {intervention.intervention_id}: "
                   f"{intervention.intervention_type.value} on {intervention.target_process}")
        
        # Send intervention request to the MCP State Coordinator
        if self.websocket:
            message = {
                'type': 'intervention_request',
                'intervention': asdict(intervention),
                'timestamp': time.time()
            }
            
            try:
                await self.websocket.send(json.dumps(message))
                logger.info(f"Intervention request sent for {intervention.intervention_id}")
            except Exception as e:
                logger.error(f"Failed to send intervention request: {e}")
        
        # Store intervention in history and database
        self.intervention_history.append(intervention)
        self._persist_intervention(intervention)
        
        # Update the process monitor status
        if intervention.target_process in self.active_monitors:
            monitor = self.active_monitors[intervention.target_process]
            monitor.status = f"intervention_{intervention.intervention_type.value}"
            self._persist_monitor(monitor)
    
    def _check_better_capability_available(self, monitor: ProcessMonitor) -> bool:
        """Check if a server with better capability is available"""
        current_server_caps = self.server_capabilities.get(monitor.server_id, {})
        current_specialization = current_server_caps.get('specializations', {}).get(monitor.task_type, 0.5)
        
        for server_id, capabilities in self.server_capabilities.items():
            if server_id == monitor.server_id:
                continue
            
            specialization = capabilities.get('specializations', {}).get(monitor.task_type, 0.0)
            if specialization > current_specialization + 0.3:  # 30% better
                return True
        
        return False
    
    def _get_historical_intervention_success(self, intervention_type: InterventionType, 
                                           task_type: str, server_id: str) -> float:
        """Get historical success rate for similar interventions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT AVG(effectiveness_score) FROM interventions 
            WHERE intervention_type = ? AND target_process LIKE ? AND source_server = ?
            AND effectiveness_score IS NOT NULL
        ''', (intervention_type.value, f"%{task_type}%", server_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result[0] is not None else 0.5
    
    def _persist_monitor(self, monitor: ProcessMonitor):
        """Persist process monitor to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO process_monitors 
            (process_id, server_id, task_type, started_at, last_update, status, 
             progress_indicators, error_count, quality_score, resource_usage, expected_completion)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            monitor.process_id, monitor.server_id, monitor.task_type,
            monitor.started_at, monitor.last_update, monitor.status,
            json.dumps(monitor.progress_indicators), monitor.error_count,
            monitor.quality_score, 
            json.dumps(monitor.resource_usage) if monitor.resource_usage else None,
            monitor.expected_completion
        ))
        
        conn.commit()
        conn.close()
    
    def _persist_intervention(self, intervention: InterventionEvent):
        """Persist intervention to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO interventions 
            (intervention_id, trigger_type, intervention_type, source_server, target_server,
             target_process, confidence, reasoning, proposed_action, timestamp, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            intervention.intervention_id, intervention.trigger.value,
            intervention.intervention_type.value, intervention.source_server,
            intervention.target_server, intervention.target_process,
            intervention.confidence, intervention.reasoning,
            json.dumps(intervention.proposed_action), intervention.timestamp,
            intervention.status
        ))
        
        conn.commit()
        conn.close()
    
    def get_intervention_analytics(self) -> Dict[str, Any]:
        """Get analytics on intervention effectiveness"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get intervention counts by type
        cursor.execute('''
            SELECT intervention_type, COUNT(*), AVG(effectiveness_score)
            FROM interventions 
            GROUP BY intervention_type
        ''')
        intervention_stats = cursor.fetchall()
        
        # Get server intervention stats
        cursor.execute('''
            SELECT source_server, COUNT(*), AVG(confidence), AVG(effectiveness_score)
            FROM interventions 
            GROUP BY source_server
        ''')
        server_stats = cursor.fetchall()
        
        conn.close()
        
        return {
            'intervention_stats': [
                {
                    'type': stat[0],
                    'count': stat[1], 
                    'avg_effectiveness': stat[2] or 0.0
                } for stat in intervention_stats
            ],
            'server_stats': [
                {
                    'server_id': stat[0],
                    'intervention_count': stat[1],
                    'avg_confidence': stat[2] or 0.0,
                    'avg_effectiveness': stat[3] or 0.0
                } for stat in server_stats
            ],
            'total_interventions': len(self.intervention_history),
            'active_monitors': len(self.active_monitors)
        }

# Example usage and integration
async def main():
    """Example usage of the Intelligent Intervention System"""
    intervention_system = IntelligentInterventionSystem()
    await intervention_system.connect_to_coordinator()
    
    # Register some example server capabilities
    intervention_system.register_server_capabilities('youtube-uvai', {
        'capabilities': ['video_analysis', 'ai_reasoning', 'transcript_processing'],
        'specializations': {'video_analysis': 0.9, 'ai_reasoning': 0.8},
        'performance_metrics': {'video_analysis': {'success_rate': 0.95}},
        'reliability_score': 0.9
    })
    
    intervention_system.register_server_capabilities('self-correcting-executor', {
        'capabilities': ['error_correction', 'code_execution', 'debugging'],
        'specializations': {'error_correction': 0.95, 'debugging': 0.9},
        'performance_metrics': {'error_correction': {'success_rate': 0.98}},
        'reliability_score': 0.95
    })
    
    # Example: Start monitoring a video analysis process
    monitor = intervention_system.start_process_monitoring(
        'video_analysis_001', 'youtube-uvai', 'video_analysis', expected_duration=300
    )
    
    # Simulate process updates that might trigger interventions
    await asyncio.sleep(1)
    
    # Simulate an error that should trigger intervention
    intervention_system.update_process_status('video_analysis_001', {
        'error_count': 3,
        'quality_score': 0.4,
        'progress_indicators': {'completion': 0.2}
    })
    
    # Keep the system running
    await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())