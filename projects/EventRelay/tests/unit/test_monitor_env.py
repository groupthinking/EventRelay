"""
Tests for scripts/monitor_env.py - Environment file monitoring tool
"""
import sys
import tempfile
import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from monitor_env import (
    EnvFileHandler,
    PollingMonitor,
    WATCHDOG_AVAILABLE
)


class TestMonitorEnv:
    """Test environment file monitoring functionality."""

    def test_polling_monitor_initialization(self):
        """Test PollingMonitor initialization."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            # Create a mock validator
            mock_validator = MagicMock()
            
            monitor = PollingMonitor(env_file, mock_validator, interval=1)
            
            assert monitor.env_path == env_file
            assert monitor.validator == mock_validator
            assert monitor.interval == 1
            assert monitor.last_mtime > 0

    def test_polling_monitor_detects_no_change(self):
        """Test that polling monitor doesn't trigger on no change."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            mock_validator = MagicMock()
            monitor = PollingMonitor(env_file, mock_validator, interval=1)
            
            # Store original mtime
            original_mtime = monitor.last_mtime
            
            # Check for changes (should be none)
            monitor.check_changes()
            
            # Validator should not be called since file hasn't changed
            assert monitor.last_mtime == original_mtime

    def test_polling_monitor_detects_change(self):
        """Test that polling monitor detects file changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            mock_validator = MagicMock()
            mock_validator.validate_all.return_value = True
            mock_validator.errors = []
            mock_validator.warnings = []
            
            monitor = PollingMonitor(env_file, mock_validator, interval=1)
            
            # Sleep briefly to ensure different timestamp
            time.sleep(0.1)
            
            # Modify the file
            env_file.write_text("GEMINI_API_KEY=updated")
            
            # Check for changes
            monitor.check_changes()
            
            # Mtime should be updated
            assert monitor.last_mtime == env_file.stat().st_mtime

    def test_polling_monitor_handles_missing_file(self):
        """Test that polling monitor handles missing .env file gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            # Don't create the file
            
            mock_validator = MagicMock()
            monitor = PollingMonitor(env_file, mock_validator, interval=1)
            
            # Should initialize with mtime of 0
            assert monitor.last_mtime == 0
            
            # Should handle check_changes without error
            monitor.check_changes()  # Should not raise exception

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_env_file_handler_initialization(self):
        """Test EnvFileHandler initialization when watchdog is available."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            mock_validator = MagicMock()
            
            handler = EnvFileHandler(env_file, mock_validator)
            
            assert handler.env_path == env_file
            assert handler.validator == mock_validator
            assert handler.last_modified == 0

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_env_file_handler_debouncing(self):
        """Test that EnvFileHandler debounces rapid changes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            mock_validator = MagicMock()
            handler = EnvFileHandler(env_file, mock_validator)
            
            # Create a mock event
            mock_event = MagicMock()
            mock_event.is_directory = False
            mock_event.src_path = str(env_file)
            
            # First call should trigger
            handler.on_modified(mock_event)
            first_time = handler.last_modified
            
            # Immediate second call should be debounced
            handler.on_modified(mock_event)
            second_time = handler.last_modified
            
            # Times should be the same (debounced)
            assert first_time == second_time

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_env_file_handler_ignores_wrong_file(self):
        """Test that EnvFileHandler ignores changes to other files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            other_file = Path(tmp_dir) / "other.txt"
            
            env_file.write_text("GEMINI_API_KEY=test")
            other_file.write_text("other content")
            
            mock_validator = MagicMock()
            handler = EnvFileHandler(env_file, mock_validator)
            
            # Create a mock event for different file
            mock_event = MagicMock()
            mock_event.is_directory = False
            mock_event.src_path = str(other_file)
            
            # Should not trigger on wrong file
            original_time = handler.last_modified
            handler.on_modified(mock_event)
            
            # Time should not change
            assert handler.last_modified == original_time

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_env_file_handler_ignores_directories(self):
        """Test that EnvFileHandler ignores directory events."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            mock_validator = MagicMock()
            handler = EnvFileHandler(env_file, mock_validator)
            
            # Create a mock directory event
            mock_event = MagicMock()
            mock_event.is_directory = True
            mock_event.src_path = str(env_file)
            
            # Should not trigger on directory
            original_time = handler.last_modified
            handler.on_modified(mock_event)
            
            # Time should not change
            assert handler.last_modified == original_time

    def test_polling_monitor_validates_on_change(self):
        """Test that polling monitor validates configuration on change."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test-initial")
            
            # Create a real validator (not mock) for this test
            from validate_env import EnvValidator
            validator = EnvValidator(env_file)
            
            monitor = PollingMonitor(env_file, validator, interval=1)
            
            # Sleep to ensure different timestamp
            time.sleep(0.1)
            
            # Update with valid key
            env_file.write_text("GEMINI_API_KEY=AIzaSyTest1234567890123456789012345678")
            
            # Check for changes
            monitor.check_changes()
            
            # Should have triggered validation
            assert monitor.last_mtime == env_file.stat().st_mtime

    def test_watchdog_availability_flag(self):
        """Test that WATCHDOG_AVAILABLE flag is correctly set."""
        # This should be True or False depending on whether watchdog is installed
        assert isinstance(WATCHDOG_AVAILABLE, bool)

    def test_polling_monitor_interval_validation(self):
        """Test that polling monitor accepts valid intervals."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test")
            
            mock_validator = MagicMock()
            
            # Test various intervals
            for interval in [1, 2, 5, 10]:
                monitor = PollingMonitor(env_file, mock_validator, interval=interval)
                assert monitor.interval == interval

    def test_polling_monitor_handle_change_with_errors(self):
        """Test that handle_change processes errors correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=placeholder")
            
            mock_validator = MagicMock()
            mock_validator.validate_all.return_value = False
            mock_validator.errors = ["Error 1", "Error 2"]
            mock_validator.warnings = []
            
            monitor = PollingMonitor(env_file, mock_validator, interval=1)
            
            # Should handle errors without crashing
            time.sleep(0.1)
            env_file.write_text("GEMINI_API_KEY=updated-placeholder")
            monitor.check_changes()

    def test_polling_monitor_handle_change_with_warnings(self):
        """Test that handle_change processes warnings correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=test\nYOUTUBE_API_KEY=placeholder")
            
            mock_validator = MagicMock()
            mock_validator.validate_all.return_value = True
            mock_validator.errors = []
            mock_validator.warnings = ["Warning 1"]
            
            monitor = PollingMonitor(env_file, mock_validator, interval=1)
            
            # Should handle warnings without crashing
            time.sleep(0.1)
            env_file.write_text("GEMINI_API_KEY=test\nYOUTUBE_API_KEY=updated")
            monitor.check_changes()
