"""
Agent Gap Monitoring Integration
==================================

This module provides hooks to integrate agent gap detection into the EventRelay
workflow. It monitors agent invocations and file access to automatically detect
when new custom agents might be beneficial.

Usage:
    from youtube_extension.services.agents.monitor import monitor_agent_usage
    
    # In your agent code:
    monitor_agent_usage(file_path="src/example.py", task="Adding new feature")
"""

import logging
from typing import Optional
import os

# Lazy import to avoid circular dependencies
_analyzer = None

def get_analyzer() -> "AgentGapAnalyzer":
    """Get or create agent gap analyzer instance"""
    global _analyzer
    if _analyzer is None:
        from .agent_gap_analyzer import AgentGapAnalyzer
        _analyzer = AgentGapAnalyzer()
    return _analyzer


def monitor_file_access(file_path: str, task_description: str = "") -> None:
    """
    Monitor file access to detect potential agent coverage gaps.
    
    Args:
        file_path: Path of file being accessed
        task_description: Description of task being performed
    """
    # Only monitor if explicitly enabled
    if not os.getenv("EVENTRELAY_MONITOR_AGENT_GAPS", "false").lower() in ("true", "1", "yes"):
        return
    
    try:
        analyzer = get_analyzer()
        analyzer.analyze_file_access(file_path, task_description)
    except Exception as e:
        # Silently fail - monitoring shouldn't break workflows
        logging.debug(f"Agent gap monitoring failed: {e}")


def monitor_error(error_type: str, context: str, frequency: int = 1) -> None:
    """
    Monitor error patterns to identify gaps.
    
    Args:
        error_type: Type/category of error
        context: Context where error occurred
        frequency: How many times this error has occurred
    """
    if not os.getenv("EVENTRELAY_MONITOR_AGENT_GAPS", "false").lower() in ("true", "1", "yes"):
        return
    
    try:
        analyzer = get_analyzer()
        analyzer.analyze_error_pattern(error_type, context, frequency)
    except Exception as e:
        logging.debug(f"Agent gap monitoring failed: {e}")


def monitor_agent_usage(
    file_path: Optional[str] = None,
    task: Optional[str] = None,
    error: Optional[tuple] = None
) -> None:
    """
    Unified monitoring function for agent usage.
    
    Args:
        file_path: Path of file being accessed
        task: Description of task being performed
        error: Tuple of (error_type, context, frequency)
    """
    if file_path or task:
        monitor_file_access(file_path or "", task or "")
    
    if error:
        error_type, context, frequency = error
        monitor_error(error_type, context, frequency)


# Context manager for monitoring code blocks
class MonitoredTask:
    """Context manager for monitoring agent-related tasks"""
    
    def __init__(self, file_path: str, task: str):
        self.file_path = file_path
        self.task = task
        self.error_occurred = False
    
    def __enter__(self):
        monitor_file_access(self.file_path, self.task)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.error_occurred = True
            error_name = exc_type.__name__
            error_context = f"{self.file_path}: {str(exc_val)}"
            monitor_error(error_name, error_context, frequency=1)
        return False  # Don't suppress exceptions
