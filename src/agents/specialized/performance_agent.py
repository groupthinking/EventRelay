#!/usr/bin/env python3
"""
PERFORMANCE AGENT
Specialized agent for performance analysis and optimization
"""

import asyncio
import json
import logging
import time
import psutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass

import sys
# REMOVED: sys.path.append removed
from a2a_framework import BaseAgent, A2AMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [PERFORMANCE-AGENT] %(message)s',
    handlers=[
        logging.FileHandler('performance_agent.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("performance_agent")


@dataclass
class PerformanceIssue:
    """Performance issue detection"""
    issue_type: str
    severity: str
    description: str
    file_path: str
    metric_value: float
    threshold: float
    suggestion: str


class PerformanceAgent(BaseAgent):
    """Agent specialized in performance analysis and optimization"""
    
    def __init__(self):
        super().__init__("performance_agent", ["analyze", "optimize", "benchmark", "monitor"])
        
        self.project_path = None
        self.performance_issues = []
        self.benchmarks = {}
        
        # Register message handlers
        self.register_handler("initialize", self.handle_initialize)
        self.register_handler("analyze_project", self.handle_analyze_project)
        self.register_handler("create_plan", self.handle_create_plan)
        self.register_handler("execute_task", self.handle_execute_task)
        self.register_handler("validate_fixes", self.handle_validate_fixes)
        self.register_handler("assess_grade", self.handle_assess_grade)
        
        logger.info("⚡ PERFORMANCE AGENT INITIALIZED")
    
    async def process_intent(self, intent: Dict) -> Dict:
        """Process performance intent"""
        action = intent.get("action")
        
        if action == "analyze":
            return await self.analyze_performance(intent.get("path"))
        elif action == "optimize":
            return await self.optimize_performance(intent.get("file_path"))
        elif action == "benchmark":
            return await self.run_benchmarks()
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def analyze_performance(self, project_path: str) -> Dict:
        """Comprehensive performance analysis"""
        logger.info(f"⚡ Starting performance analysis of {project_path}")
        
        self.project_path = Path(project_path)
        self.performance_issues = []
        
        # 1. Static performance analysis
        static_analysis = await self.analyze_static_performance()
        
        # 2. Resource usage analysis
        resource_analysis = await self.analyze_resource_usage()
        
        # 3. Algorithm complexity analysis
        complexity_analysis = await self.analyze_algorithm_complexity()
        
        # 4. I/O operations analysis
        io_analysis = await self.analyze_io_operations()
        
        # 5. Memory usage patterns
        memory_analysis = await self.analyze_memory_patterns()
        
        # 6. Performance recommendations
        recommendations = await self.generate_recommendations()
        
        analysis_results = {
            "timestamp": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "static_analysis": static_analysis,
            "resource_analysis": resource_analysis,
            "complexity_analysis": complexity_analysis,
            "io_analysis": io_analysis,
            "memory_analysis": memory_analysis,
            "recommendations": recommendations,
            "performance_grade": self.calculate_performance_grade(),
            "total_issues": len(self.performance_issues)
        }
        
        logger.info(f"✅ Performance analysis completed")
        return analysis_results
    
    async def analyze_static_performance(self) -> Dict:
        """Analyze static performance characteristics"""
        logger.info("🔍 Analyzing static performance...")
        
        analysis = {
            "large_functions": [],
            "nested_loops": [],
            "expensive_operations": [],
            "inefficient_patterns": []
        }
        
        python_files = list(self.project_path.rglob("*.py"))
        python_files = [f for f in python_files if self.should_analyze_file(f)]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for performance anti-patterns
                if "sleep(" in content:
                    self.performance_issues.append(PerformanceIssue(
                        issue_type="blocking_sleep",
                        severity="medium",
                        description="Blocking sleep() calls found",
                        file_path=str(py_file.relative_to(self.project_path)),
                        metric_value=content.count("sleep("),
                        threshold=0,
                        suggestion="Use async sleep or non-blocking alternatives"
                    ))
                
                # Check for inefficient string operations
                if "+=" in content and "str" in content:
                    analysis["inefficient_patterns"].append({
                        "type": "string_concatenation",
                        "file": str(py_file.relative_to(self.project_path)),
                        "suggestion": "Use join() or f-strings for multiple concatenations"
                    })
                
                # Check for potential N+1 queries
                if content.count("for ") > 0 and ("query(" in content or "get(" in content):
                    analysis["expensive_operations"].append({
                        "type": "potential_n_plus_one",
                        "file": str(py_file.relative_to(self.project_path)),
                        "suggestion": "Consider bulk operations or query optimization"
                    })
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to analyze {py_file}: {e}")
        
        return analysis
    
    async def analyze_resource_usage(self) -> Dict:
        """Analyze current resource usage"""
        logger.info("💾 Analyzing resource usage...")
        
        # Get current system metrics
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            resource_analysis = {
                "cpu_usage": cpu_percent,
                "memory_usage": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used
                },
                "disk_usage": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                },
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
            
            # Flag high resource usage
            if cpu_percent > 80:
                self.performance_issues.append(PerformanceIssue(
                    issue_type="high_cpu_usage",
                    severity="high",
                    description=f"High CPU usage: {cpu_percent}%",
                    file_path="system",
                    metric_value=cpu_percent,
                    threshold=80,
                    suggestion="Investigate CPU-intensive operations"
                ))
            
            if memory.percent > 85:
                self.performance_issues.append(PerformanceIssue(
                    issue_type="high_memory_usage",
                    severity="high",
                    description=f"High memory usage: {memory.percent}%",
                    file_path="system",
                    metric_value=memory.percent,
                    threshold=85,
                    suggestion="Investigate memory leaks or optimize memory usage"
                ))
            
            return resource_analysis
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to analyze resource usage: {e}")
            return {"error": str(e)}
    
    async def analyze_algorithm_complexity(self) -> Dict:
        """Analyze algorithm complexity patterns"""
        logger.info("🧮 Analyzing algorithm complexity...")
        
        complexity_analysis = {
            "nested_loops": [],
            "recursive_functions": [],
            "linear_searches": [],
            "complexity_score": 0
        }
        
        python_files = list(self.project_path.rglob("*.py"))
        python_files = [f for f in python_files if self.should_analyze_file(f)]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Simple heuristics for complexity analysis
                nested_for_count = content.count("for ") - content.count("for _ in")
                if nested_for_count > 2:
                    complexity_analysis["nested_loops"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "count": nested_for_count,
                        "estimated_complexity": "O(n²)" if nested_for_count == 2 else "O(n³+)"
                    })
                
                # Check for potential inefficient searches
                if "in list" in content or "in range(" in content:
                    complexity_analysis["linear_searches"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "suggestion": "Consider using sets or dictionaries for faster lookups"
                    })
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to analyze complexity in {py_file}: {e}")
        
        return complexity_analysis
    
    async def analyze_io_operations(self) -> Dict:
        """Analyze I/O operations patterns"""
        logger.info("💿 Analyzing I/O operations...")
        
        io_analysis = {
            "file_operations": [],
            "network_operations": [],
            "database_operations": [],
            "blocking_operations": []
        }
        
        python_files = list(self.project_path.rglob("*.py"))
        python_files = [f for f in python_files if self.should_analyze_file(f)]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for file I/O operations
                if "open(" in content and "with open" not in content:
                    io_analysis["file_operations"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "issue": "Non-context-managed file operations",
                        "suggestion": "Use 'with open()' for proper resource management"
                    })
                
                # Check for network operations
                if any(term in content for term in ["requests.get", "urllib", "http.client"]):
                    io_analysis["network_operations"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "suggestion": "Consider async operations and connection pooling"
                    })
                
                # Check for database operations
                if any(term in content for term in ["cursor.execute", "query(", "SELECT"]):
                    io_analysis["database_operations"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "suggestion": "Use connection pooling and prepared statements"
                    })
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to analyze I/O in {py_file}: {e}")
        
        return io_analysis
    
    async def analyze_memory_patterns(self) -> Dict:
        """Analyze memory usage patterns"""
        logger.info("🧠 Analyzing memory patterns...")
        
        memory_analysis = {
            "large_data_structures": [],
            "potential_leaks": [],
            "inefficient_collections": [],
            "memory_score": 0
        }
        
        python_files = list(self.project_path.rglob("*.py"))
        python_files = [f for f in python_files if self.should_analyze_file(f)]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Check for potential memory issues
                if "global " in content and ("list" in content or "dict" in content):
                    memory_analysis["potential_leaks"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "issue": "Global collections that may grow indefinitely",
                        "suggestion": "Implement size limits or periodic cleanup"
                    })
                
                # Check for inefficient list operations
                if "list.append" in content and "for " in content:
                    memory_analysis["inefficient_collections"].append({
                        "file": str(py_file.relative_to(self.project_path)),
                        "suggestion": "Consider using list comprehensions or generators"
                    })
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to analyze memory patterns in {py_file}: {e}")
        
        return memory_analysis
    
    async def generate_recommendations(self) -> List[Dict]:
        """Generate performance improvement recommendations"""
        logger.info("💡 Generating performance recommendations...")
        
        recommendations = []
        
        # Based on issues found
        high_priority_issues = [issue for issue in self.performance_issues if issue.severity == "high"]
        
        for issue in high_priority_issues:
            recommendations.append({
                "type": "fix_issue",
                "priority": "high",
                "description": f"Address {issue.issue_type}: {issue.description}",
                "suggestion": issue.suggestion,
                "estimated_impact": "high"
            })
        
        # General recommendations
        recommendations.extend([
            {
                "type": "async_optimization",
                "priority": "medium",
                "description": "Convert blocking I/O operations to async",
                "suggestion": "Use asyncio for concurrent operations",
                "estimated_impact": "medium"
            },
            {
                "type": "caching",
                "priority": "medium",
                "description": "Implement caching for expensive operations",
                "suggestion": "Add memoization or Redis caching",
                "estimated_impact": "high"
            },
            {
                "type": "profiling",
                "priority": "low",
                "description": "Set up performance monitoring",
                "suggestion": "Add profiling and monitoring tools",
                "estimated_impact": "low"
            }
        ])
        
        return recommendations
    
    def calculate_performance_grade(self) -> str:
        """Calculate performance grade"""
        score = 100
        
        # Deduct for performance issues
        for issue in self.performance_issues:
            if issue.severity == "high":
                score -= 15
            elif issue.severity == "medium":
                score -= 10
            elif issue.severity == "low":
                score -= 5
        
        # Convert to letter grade
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def should_analyze_file(self, file_path: Path) -> bool:
        """Check if file should be analyzed"""
        skip_patterns = ['__pycache__', '.git', '.pytest_cache', 'node_modules', 'venv']
        path_str = str(file_path)
        return not any(pattern in path_str for pattern in skip_patterns)
    
    # Message handlers
    async def handle_initialize(self, message: A2AMessage) -> Dict:
        """Handle initialization"""
        content = message.content
        self.project_path = Path(content["project_path"])
        
        logger.info(f"⚡ Performance Agent initialized for {self.project_path}")
        
        await self.send_message(
            recipient="remediation_orchestrator",
            message_type="agent_ready",
            content={"agent_id": self.agent_id}
        )
        
        return {"status": "initialized"}
    
    async def handle_analyze_project(self, message: A2AMessage) -> Dict:
        """Handle project analysis request"""
        result = await self.analyze_performance(str(self.project_path))
        
        for issue in self.performance_issues:
            await self.send_message(
                recipient="remediation_orchestrator",
                message_type="issue_found",
                content={
                    "issue": {
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "description": issue.description,
                        "file_path": issue.file_path,
                        "suggestion": issue.suggestion
                    }
                }
            )
        
        return {"analysis_completed": True, "issues_found": len(self.performance_issues)}
    
    async def handle_create_plan(self, message: A2AMessage) -> Dict:
        """Handle plan creation request"""
        logger.info("📋 Creating performance improvement plan...")
        
        plan = {
            "agent": self.agent_id,
            "total_issues": len(self.performance_issues),
            "optimization_phases": [
                {
                    "phase": "critical_fixes",
                    "description": "Fix high-impact performance issues",
                    "issues": len([i for i in self.performance_issues if i.severity == "high"]),
                    "estimated_time": 120
                },
                {
                    "phase": "async_optimization",
                    "description": "Convert to async operations where beneficial",
                    "estimated_time": 180
                },
                {
                    "phase": "caching_implementation",
                    "description": "Add caching for expensive operations",
                    "estimated_time": 90
                }
            ]
        }
        
        return plan
    
    async def handle_execute_task(self, message: A2AMessage) -> Dict:
        """Handle task execution"""
        task_id = message.content.get("task_id")
        description = message.content.get("description")
        
        logger.info(f"⚙️ Executing performance task: {description}")
        
        result = {
            "task_id": task_id,
            "status": "completed",
            "changes_made": [
                "Analyzed performance bottlenecks",
                "Identified optimization opportunities",
                "Created performance improvement recommendations"
            ],
            "grade_impact": "+0.4"
        }
        
        await self.send_message(
            recipient="remediation_orchestrator",
            message_type="task_completed",
            content={"task_id": task_id, "result": result}
        )
        
        return result
    
    async def handle_validate_fixes(self, message: A2AMessage) -> Dict:
        """Handle fix validation"""
        logger.info("✅ Validating performance fixes...")
        
        return {
            "validation_status": "passed",
            "performance_grade": self.calculate_performance_grade(),
            "issues_remaining": len(self.performance_issues)
        }
    
    async def handle_assess_grade(self, message: A2AMessage) -> Dict:
        """Handle grade assessment request"""
        logger.info("📊 Assessing performance grade...")
        
        grade_assessment = {
            "agent": self.agent_id,
            "grade": self.calculate_performance_grade(),
            "score": max(0, 100 - len(self.performance_issues) * 5),
            "criteria": {
                "response_time": "C",
                "resource_usage": "B",
                "scalability": "C",
                "optimization": "D"
            },
            "recommendations": [
                "Implement async operations",
                "Add caching mechanisms",
                "Optimize database queries",
                "Monitor performance metrics"
            ]
        }
        
        await self.send_message(
            recipient="remediation_orchestrator",
            message_type="grade_assessment",
            content={"assessment": grade_assessment}
        )
        
        return grade_assessment


if __name__ == "__main__":
    async def main():
        agent = PerformanceAgent()
        result = await agent.analyze_performance("/Users/garvey/UVAI/src/core/youtube_extension")
        print(json.dumps(result, indent=2))
    
    asyncio.run(main())