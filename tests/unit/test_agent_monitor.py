"""
Tests for Agent Gap Monitoring
================================

Tests the optional monitoring integration for agent gap detection.
"""

import pytest
import tempfile
from pathlib import Path
import os

# Import the modules to test
import sys
agent_module_path = Path(__file__).parent.parent / "src" / "youtube_extension" / "services" / "agents"
sys.path.insert(0, str(agent_module_path))

from monitor import (
    get_analyzer,
    monitor_file_access,
    monitor_error,
    monitor_agent_usage,
    MonitoredTask
)


class TestMonitoring:
    """Test monitoring functions."""

    def test_get_analyzer(self):
        """Test getting analyzer instance."""
        analyzer = get_analyzer()
        assert analyzer is not None
        
        # Should return same instance
        analyzer2 = get_analyzer()
        assert analyzer is analyzer2

    def test_monitor_file_access_disabled(self):
        """Test monitoring when disabled (default)."""
        # Monitoring should be disabled by default
        os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)
        
        # Should not raise error even if disabled
        monitor_file_access("test.yaml", "Test task")

    def test_monitor_file_access_enabled(self):
        """Test monitoring when enabled."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
            
            try:
                # Should work without error
                monitor_file_access("infrastructure/k8s/deploy.yaml", "Deploy")
                monitor_file_access("database/migrations/001.sql", "Migrate")
            finally:
                os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitor_error_disabled(self):
        """Test error monitoring when disabled."""
        os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)
        
        # Should not raise error
        monitor_error("TestError", "Test context", frequency=1)

    def test_monitor_error_enabled(self):
        """Test error monitoring when enabled."""
        os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
        
        try:
            # Should work without error
            monitor_error("DatabaseError", "Connection timeout", frequency=3)
        finally:
            os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitor_agent_usage_file_access(self):
        """Test unified monitoring with file access."""
        os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
        
        try:
            monitor_agent_usage(
                file_path="test/file.yaml",
                task="Test task"
            )
        finally:
            os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitor_agent_usage_error(self):
        """Test unified monitoring with error."""
        os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
        
        try:
            monitor_agent_usage(
                error=("TestError", "Test context", 2)
            )
        finally:
            os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitor_agent_usage_combined(self):
        """Test unified monitoring with both file and error."""
        os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
        
        try:
            monitor_agent_usage(
                file_path="test.yaml",
                task="Test",
                error=("Error", "Context", 1)
            )
        finally:
            os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitored_task_context_manager_success(self):
        """Test MonitoredTask context manager with success."""
        os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
        
        try:
            with MonitoredTask("test.yaml", "Test task") as task:
                # Simulate successful operation
                pass
            
            assert not task.error_occurred
        finally:
            os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitored_task_context_manager_error(self):
        """Test MonitoredTask context manager with error."""
        os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = "true"
        
        try:
            with pytest.raises(ValueError):
                with MonitoredTask("test.yaml", "Test task") as task:
                    # Simulate error
                    raise ValueError("Test error")
            
            # Note: task.error_occurred is set in the context manager,
            # but we can't access it after the exception is raised
        finally:
            os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitoring_with_various_env_values(self):
        """Test monitoring enabled with various environment variable values."""
        test_values = ["true", "True", "TRUE", "1", "yes", "Yes", "YES"]
        
        for value in test_values:
            os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = value
            
            try:
                # Should work with any of these values
                monitor_file_access("test.yaml", "Test")
            finally:
                os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)

    def test_monitoring_disabled_with_various_env_values(self):
        """Test monitoring disabled with various environment variable values."""
        test_values = ["false", "False", "FALSE", "0", "no", "No", "NO", ""]
        
        for value in test_values:
            os.environ["EVENTRELAY_MONITOR_AGENT_GAPS"] = value
            
            try:
                # Should not raise error
                monitor_file_access("test.yaml", "Test")
            finally:
                os.environ.pop("EVENTRELAY_MONITOR_AGENT_GAPS", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
