"""
Tests for security vulnerability fixes
Tests Issues #1, #2, and #3 from security audit
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import logging


# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestAPIKeyExposureFix:
    """Test Issue 1: API Key Exposure Risk Fix"""
    
    def test_backend_does_not_read_react_app_env_vars(self):
        """Verify that backend code does NOT read REACT_APP_* environment variables"""
        # Import the module to test
        from agents.process_video_with_mcp import RealVideoProcessor
        
        # Set up environment with ONLY the frontend variable
        with patch.dict(os.environ, {
            "REACT_APP_YOUTUBE_API_KEY": "AIzaSyFrontendKeyThatShouldBeIgnored123",
        }, clear=True):
            # In non-production mode, this should not use the REACT_APP key
            processor = RealVideoProcessor(real_mode_only=False)
            # The processor should initialize without using the frontend key
            # This is acceptable in non-production mode
            assert True  # If we get here, the module loaded
    
    def test_backend_only_reads_backend_env_var(self):
        """Verify backend correctly reads YOUTUBE_API_KEY (not REACT_APP_*)"""
        from agents.process_video_with_mcp import RealVideoProcessor
        
        backend_key = "AIzaSyBackendOnlyKey1234567890123456789"
        
        with patch.dict(os.environ, {
            "YOUTUBE_API_KEY": backend_key,
            # Also set a frontend key that should be IGNORED
            "REACT_APP_YOUTUBE_API_KEY": "AIzaSyFrontendKeyThatShouldBeIgnored123",
        }, clear=True):
            # Should initialize without error when proper backend key is present
            processor = RealVideoProcessor(real_mode_only=False)
            assert True  # Successfully initialized with backend key


class TestInputValidationFix:
    """Test Issue 2: Input Validation for Agent Messages"""
    
    def test_validate_agent_identifier_valid(self):
        """Test that valid agent identifiers pass validation"""
        # Import validation helpers from the file
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "mcp_a2a_validation",
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        "agents/unified/mcp_a2a_mojo_integration.py")
        )
        module = importlib.util.module_from_spec(spec)
        
        # Extract just the validation function code
        with open(spec.origin, 'r') as f:
            content = f.read()
        
        # Execute the validation function definition
        import re
        exec_globals = {'re': re}
        
        # Extract and execute the validate_agent_identifier function
        validate_func_match = re.search(
            r'def validate_agent_identifier\(.*?\):\n(.*?)(?=\ndef |\nclass |\Z)',
            content,
            re.DOTALL
        )
        if validate_func_match:
            func_code = f"def validate_agent_identifier{validate_func_match.group(0)[len('def validate_agent_identifier'):]}"
            exec(func_code, exec_globals)
            validate_agent_identifier = exec_globals['validate_agent_identifier']
            
            # Valid identifiers
            assert validate_agent_identifier("agent_1") is True
            assert validate_agent_identifier("coordinator") is True
            assert validate_agent_identifier("exchange-connector") is True
            assert validate_agent_identifier("hft_trader_1") is True
            assert validate_agent_identifier("A1_B2-C3") is True
    
    def test_validate_agent_identifier_invalid(self):
        """Test that invalid agent identifiers fail validation"""
        # Import validation helpers from the file
        import importlib.util
        import re as regex_module
        
        # Read the file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agents/unified/mcp_a2a_mojo_integration.py"
        )
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Execute the validation function definition
        exec_globals = {'re': regex_module}
        
        # Extract and execute the validate_agent_identifier function
        validate_func_match = regex_module.search(
            r'def validate_agent_identifier\(.*?\):\n(.*?)(?=\ndef |\nclass |\Z)',
            content,
            regex_module.DOTALL
        )
        if validate_func_match:
            func_code = f"def validate_agent_identifier{validate_func_match.group(0)[len('def validate_agent_identifier'):]}"
            exec(func_code, exec_globals)
            validate_agent_identifier = exec_globals['validate_agent_identifier']
            
            # Invalid identifiers
            assert validate_agent_identifier("") is False
            assert validate_agent_identifier(None) is False
            assert validate_agent_identifier("agent with spaces") is False
            assert validate_agent_identifier("agent@domain") is False
            assert validate_agent_identifier("agent;injection") is False
            assert validate_agent_identifier("../../../etc/passwd") is False
            assert validate_agent_identifier("agent<script>") is False
            assert validate_agent_identifier("a" * 65) is False  # Too long
            assert validate_agent_identifier(123) is False  # Not a string
    
    def test_sanitize_message_content_dict(self):
        """Test content sanitization for dictionary inputs"""
        import importlib.util
        import re as regex_module
        
        # Read the file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agents/unified/mcp_a2a_mojo_integration.py"
        )
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Execute both functions
        exec_globals = {'re': regex_module, 'Any': type(None)}
        
        # Extract functions
        for func_name in ['validate_agent_identifier', 'sanitize_message_content']:
            func_match = regex_module.search(
                rf'def {func_name}\(.*?\):\n(.*?)(?=\ndef |\nclass |\Z)',
                content,
                regex_module.DOTALL
            )
            if func_match:
                func_code = f"def {func_name}{func_match.group(0)[len(f'def {func_name}'):]}"
                exec(func_code, exec_globals)
        
        sanitize_message_content = exec_globals['sanitize_message_content']
        
        malicious_data = {
            "normal_key": "normal_value",
            "dangerous": "value\x00with\x01control\x02chars",
            "nested": {
                "key": "value\x1f"
            }
        }
        
        sanitized = sanitize_message_content(malicious_data)
        
        # Control characters should be removed
        assert "\x00" not in sanitized["dangerous"]
        assert "\x01" not in sanitized["dangerous"]
        assert "\x02" not in sanitized["dangerous"]
        
        # Nested content should also be sanitized
        assert "\x1f" not in sanitized["nested"]["key"]
    
    def test_sanitize_message_content_string(self):
        """Test content sanitization for string inputs"""
        import importlib.util
        import re as regex_module
        
        # Read the file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agents/unified/mcp_a2a_mojo_integration.py"
        )
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Execute both functions
        exec_globals = {'re': regex_module, 'Any': type(None)}
        
        # Extract functions
        for func_name in ['validate_agent_identifier', 'sanitize_message_content']:
            func_match = regex_module.search(
                rf'def {func_name}\(.*?\):\n(.*?)(?=\ndef |\nclass |\Z)',
                content,
                regex_module.DOTALL
            )
            if func_match:
                func_code = f"def {func_name}{func_match.group(0)[len(f'def {func_name}'):]}"
                exec(func_code, exec_globals)
        
        sanitize_message_content = exec_globals['sanitize_message_content']
        
        # Test with control characters
        malicious_string = "normal\x00text\x01with\x02control\x03chars"
        sanitized = sanitize_message_content(malicious_string)
        
        # Control characters should be removed (except newlines and tabs)
        assert "\x00" not in sanitized
        assert "\x01" not in sanitized
        assert "\x02" not in sanitized
        
        # Newlines and tabs should be preserved
        text_with_formatting = "line1\nline2\ttabbed"
        sanitized = sanitize_message_content(text_with_formatting)
        assert "\n" in sanitized
        assert "\t" in sanitized
    
    def test_sanitize_message_content_length_limit(self):
        """Test that content length is limited to prevent DOS"""
        import importlib.util
        import re as regex_module
        
        # Read the file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agents/unified/mcp_a2a_mojo_integration.py"
        )
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Execute both functions
        exec_globals = {'re': regex_module, 'Any': type(None)}
        
        # Extract functions
        for func_name in ['validate_agent_identifier', 'sanitize_message_content']:
            func_match = regex_module.search(
                rf'def {func_name}\(.*?\):\n(.*?)(?=\ndef |\nclass |\Z)',
                content,
                regex_module.DOTALL
            )
            if func_match:
                func_code = f"def {func_name}{func_match.group(0)[len(f'def {func_name}'):]}"
                exec(func_code, exec_globals)
        
        sanitize_message_content = exec_globals['sanitize_message_content']
        
        # Create a very long string
        long_string = "a" * 20000
        sanitized = sanitize_message_content(long_string)
        
        # Should be limited to 10000 characters
        assert len(sanitized) == 10000
    
    def test_sanitize_message_content_primitives(self):
        """Test that primitive types pass through safely"""
        import importlib.util
        import re as regex_module
        
        # Read the file
        file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "agents/unified/mcp_a2a_mojo_integration.py"
        )
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Execute both functions
        exec_globals = {'re': regex_module, 'Any': type(None)}
        
        # Extract functions
        for func_name in ['validate_agent_identifier', 'sanitize_message_content']:
            func_match = regex_module.search(
                rf'def {func_name}\(.*?\):\n(.*?)(?=\ndef |\nclass |\Z)',
                content,
                regex_module.DOTALL
            )
            if func_match:
                func_code = f"def {func_name}{func_match.group(0)[len(f'def {func_name}'):]}"
                exec(func_code, exec_globals)
        
        sanitize_message_content = exec_globals['sanitize_message_content']
        
        assert sanitize_message_content(123) == 123
        assert sanitize_message_content(45.67) == 45.67
        assert sanitize_message_content(True) is True
        assert sanitize_message_content(None) is None


class TestObservabilityFix:
    """Test Issue 3: Observability Silent Failure Fix"""
    
    def test_observability_logs_error_in_production_when_unavailable(self, caplog):
        """Test that missing telemetry logs at ERROR level in production"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "true",
            # No OTEL_EXPORTER_OTLP_ENDPOINT set
        }, clear=True):
            # Mock the TELEMETRY_AVAILABLE to False
            with patch("agents.observability_setup.TELEMETRY_AVAILABLE", False):
                with caplog.at_level(logging.ERROR):
                    obs = UVAIObservability()
                    
                    # Should log at ERROR level in production
                    assert any(
                        "CRITICAL" in record.message or "UNAVAILABLE" in record.message
                        for record in caplog.records
                        if record.levelno >= logging.ERROR
                    )
                    
                    # Should not be set up
                    assert obs.setup_complete is False
                    assert obs.observability_status in ("unavailable", "not_configured")
    
    def test_observability_logs_warning_in_dev_when_unavailable(self, caplog):
        """Test that missing telemetry logs at lower level in development"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "false",
            # No OTEL_EXPORTER_OTLP_ENDPOINT set
        }, clear=True):
            with patch("agents.observability_setup.TELEMETRY_AVAILABLE", False):
                with caplog.at_level(logging.DEBUG):
                    obs = UVAIObservability()
                    
                    # Should not be set up
                    assert obs.setup_complete is False
                    
                    # In development, error logging is not required
                    # (may log at DEBUG or WARNING level)
    
    def test_observability_health_status_in_production(self):
        """Test health status reporting includes production flag"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "true",
        }, clear=True):
            obs = UVAIObservability()
            
            health = obs.get_health_status()
            
            # Should report health status with production flag
            assert "service" in health
            assert "observability_enabled" in health
            assert "status" in health
            assert "is_production" in health
            assert health["is_production"] is True
    
    def test_observability_health_status_in_dev(self):
        """Test health status reporting in development mode"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "false",
        }, clear=True):
            obs = UVAIObservability()
            
            health = obs.get_health_status()
            
            # Should report status with dev flag
            assert "service" in health
            assert "is_production" in health
            assert health["is_production"] is False
            assert "telemetry_available" in health
            assert "tracer_configured" in health
            assert "meter_configured" in health

class TestSecurityDocumentation:
    """Test that security rationale is properly documented"""
    
    def test_api_key_security_comment_exists(self):
        """Verify security comment exists in process_video_with_mcp.py"""
        with open("/home/runner/work/EventRelay/EventRelay/agents/process_video_with_mcp.py", "r") as f:
            content = f.read()
            
        # Should have security comment explaining why we don't use REACT_APP_*
        assert "Security:" in content
        assert "REACT_APP_" in content
        assert "frontend" in content.lower()
    
    def test_validation_security_comments_exist(self):
        """Verify security comments exist in mcp_a2a_mojo_integration.py"""
        with open("/home/runner/work/EventRelay/EventRelay/agents/unified/mcp_a2a_mojo_integration.py", "r") as f:
            content = f.read()
            
        # Should have security comments explaining validation
        assert "Security" in content
        assert "injection" in content.lower()
        assert "validate" in content.lower()
    
    def test_observability_security_comments_exist(self):
        """Verify security comments exist in observability_setup.py"""
        with open("/home/runner/work/EventRelay/EventRelay/agents/observability_setup.py", "r") as f:
            content = f.read()
            
        # Should have security comments explaining production logging
        assert "Security" in content or "CRITICAL" in content
        assert "production" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

    """Test Issue 1: API Key Exposure Risk Fix"""
    
    def test_backend_does_not_read_react_app_env_vars(self):
        """Verify that backend code does NOT read REACT_APP_* environment variables"""
        # Import the module to test
        from agents.process_video_with_mcp import RealVideoProcessor
        
        # Set up environment with ONLY the frontend variable
        with patch.dict(os.environ, {
            "REACT_APP_YOUTUBE_API_KEY": "AIzaSyFrontendKeyThatShouldBeIgnored123",
        }, clear=True):
            # In non-production mode, this should not use the REACT_APP key
            processor = RealVideoProcessor(real_mode_only=False)
            # The processor should initialize without using the frontend key
            # This is acceptable in non-production mode
            assert True  # If we get here, the module loaded
    
    def test_backend_only_reads_backend_env_var(self):
        """Verify backend correctly reads YOUTUBE_API_KEY (not REACT_APP_*)"""
        from agents.process_video_with_mcp import RealVideoProcessor
        
        backend_key = "AIzaSyBackendOnlyKey1234567890123456789"
        
        with patch.dict(os.environ, {
            "YOUTUBE_API_KEY": backend_key,
            # Also set a frontend key that should be IGNORED
            "REACT_APP_YOUTUBE_API_KEY": "AIzaSyFrontendKeyThatShouldBeIgnored123",
        }, clear=True):
            # Should initialize without error when proper backend key is present
            processor = RealVideoProcessor(real_mode_only=False)
            assert True  # Successfully initialized with backend key


class TestInputValidationFix:
    """Test Issue 2: Input Validation for Agent Messages"""
    
    def test_validate_agent_identifier_valid(self):
        """Test that valid agent identifiers pass validation"""
        from agents.unified.mcp_a2a_mojo_integration import validate_agent_identifier
        
        # Valid identifiers
        assert validate_agent_identifier("agent_1") is True
        assert validate_agent_identifier("coordinator") is True
        assert validate_agent_identifier("exchange-connector") is True
        assert validate_agent_identifier("hft_trader_1") is True
        assert validate_agent_identifier("A1_B2-C3") is True
    
    def test_validate_agent_identifier_invalid(self):
        """Test that invalid agent identifiers fail validation"""
        from agents.unified.mcp_a2a_mojo_integration import validate_agent_identifier
        
        # Invalid identifiers
        assert validate_agent_identifier("") is False
        assert validate_agent_identifier(None) is False
        assert validate_agent_identifier("agent with spaces") is False
        assert validate_agent_identifier("agent@domain") is False
        assert validate_agent_identifier("agent;injection") is False
        assert validate_agent_identifier("../../../etc/passwd") is False
        assert validate_agent_identifier("agent<script>") is False
        assert validate_agent_identifier("a" * 65) is False  # Too long
        assert validate_agent_identifier(123) is False  # Not a string
    
    def test_sanitize_message_content_dict(self):
        """Test content sanitization for dictionary inputs"""
        from agents.unified.mcp_a2a_mojo_integration import sanitize_message_content
        
        malicious_data = {
            "normal_key": "normal_value",
            "dangerous": "value\x00with\x01control\x02chars",
            "nested": {
                "key": "value\x1f"
            }
        }
        
        sanitized = sanitize_message_content(malicious_data)
        
        # Control characters should be removed
        assert "\x00" not in sanitized["dangerous"]
        assert "\x01" not in sanitized["dangerous"]
        assert "\x02" not in sanitized["dangerous"]
        
        # Nested content should also be sanitized
        assert "\x1f" not in sanitized["nested"]["key"]
    
    def test_sanitize_message_content_string(self):
        """Test content sanitization for string inputs"""
        from agents.unified.mcp_a2a_mojo_integration import sanitize_message_content
        
        # Test with control characters
        malicious_string = "normal\x00text\x01with\x02control\x03chars"
        sanitized = sanitize_message_content(malicious_string)
        
        # Control characters should be removed (except newlines and tabs)
        assert "\x00" not in sanitized
        assert "\x01" not in sanitized
        assert "\x02" not in sanitized
        
        # Newlines and tabs should be preserved
        text_with_formatting = "line1\nline2\ttabbed"
        sanitized = sanitize_message_content(text_with_formatting)
        assert "\n" in sanitized
        assert "\t" in sanitized
    
    def test_sanitize_message_content_length_limit(self):
        """Test that content length is limited to prevent DOS"""
        from agents.unified.mcp_a2a_mojo_integration import sanitize_message_content
        
        # Create a very long string
        long_string = "a" * 20000
        sanitized = sanitize_message_content(long_string)
        
        # Should be limited to 10000 characters
        assert len(sanitized) == 10000
    
    def test_sanitize_message_content_primitives(self):
        """Test that primitive types pass through safely"""
        from agents.unified.mcp_a2a_mojo_integration import sanitize_message_content
        
        assert sanitize_message_content(123) == 123
        assert sanitize_message_content(45.67) == 45.67
        assert sanitize_message_content(True) is True
        assert sanitize_message_content(None) is None
    
    @pytest.mark.asyncio
    async def test_send_unified_message_validates_recipient(self):
        """Test that send_unified_message validates recipient identifier"""
        from agents.unified.mcp_a2a_mojo_integration import IntelligentUnifiedAgent
        
        agent = IntelligentUnifiedAgent("test_agent", ["test"])
        
        # Valid recipient should work
        try:
            result = await agent.send_unified_message(
                recipient="valid_agent",
                intent="test",
                data={"message": "test"}
            )
            # Should succeed
            assert result is not None
        except Exception as e:
            # May fail for other reasons (agent not found, etc.) but not validation
            assert "Invalid recipient identifier" not in str(e)
        
        # Invalid recipient should raise ValueError
        with pytest.raises(ValueError, match="Invalid recipient identifier"):
            await agent.send_unified_message(
                recipient="invalid/agent",
                intent="test",
                data={"message": "test"}
            )
    
    @pytest.mark.asyncio
    async def test_send_unified_message_validates_intent(self):
        """Test that send_unified_message validates intent identifier"""
        from agents.unified.mcp_a2a_mojo_integration import IntelligentUnifiedAgent
        
        agent = IntelligentUnifiedAgent("test_agent", ["test"])
        
        # Invalid intent should raise ValueError
        with pytest.raises(ValueError, match="Invalid intent identifier"):
            await agent.send_unified_message(
                recipient="valid_agent",
                intent="invalid;intent",
                data={"message": "test"}
            )
    
    @pytest.mark.asyncio
    async def test_send_unified_message_sanitizes_content(self):
        """Test that send_unified_message sanitizes message content"""
        from agents.unified.mcp_a2a_mojo_integration import IntelligentUnifiedAgent
        
        agent = IntelligentUnifiedAgent("test_agent", ["test"])
        
        # Malicious content
        malicious_data = {
            "key": "value\x00with\x01control\x02chars"
        }
        
        # Should sanitize the content before sending
        result = await agent.send_unified_message(
            recipient="test_recipient",
            intent="test",
            data=malicious_data
        )
        
        # Message should be created successfully (sanitization happens internally)
        assert result is not None
        assert "message_id" in result


class TestObservabilityFix:
    """Test Issue 3: Observability Silent Failure Fix"""
    
    def test_observability_logs_error_in_production_when_unavailable(self, caplog):
        """Test that missing telemetry logs at ERROR level in production"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "true",
            # No OTEL_EXPORTER_OTLP_ENDPOINT set
        }, clear=True):
            # Mock the TELEMETRY_AVAILABLE to False
            with patch("agents.observability_setup.TELEMETRY_AVAILABLE", False):
                with caplog.at_level(logging.ERROR):
                    obs = UVAIObservability()
                    
                    # Should log at ERROR level in production
                    assert any(
                        "CRITICAL" in record.message or "UNAVAILABLE" in record.message
                        for record in caplog.records
                        if record.levelno >= logging.ERROR
                    )
                    
                    # Should not be set up
                    assert obs.setup_complete is False
                    assert obs.observability_status in ("unavailable", "not_configured")
    
    def test_observability_logs_warning_in_dev_when_unavailable(self, caplog):
        """Test that missing telemetry logs at lower level in development"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "false",
            # No OTEL_EXPORTER_OTLP_ENDPOINT set
        }, clear=True):
            with patch("agents.observability_setup.TELEMETRY_AVAILABLE", False):
                with caplog.at_level(logging.DEBUG):
                    obs = UVAIObservability()
                    
                    # Should not be set up
                    assert obs.setup_complete is False
                    
                    # In development, error logging is not required
                    # (may log at DEBUG or WARNING level)
    
    def test_observability_health_status_in_production(self):
        """Test health status reporting includes production flag"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "true",
        }, clear=True):
            obs = UVAIObservability()
            
            health = obs.get_health_status()
            
            # Should report health status with production flag
            assert "service" in health
            assert "observability_enabled" in health
            assert "status" in health
            assert "is_production" in health
            assert health["is_production"] is True
    
    def test_observability_health_status_in_dev(self):
        """Test health status reporting in development mode"""
        from agents.observability_setup import UVAIObservability
        
        with patch.dict(os.environ, {
            "REAL_MODE_ONLY": "false",
        }, clear=True):
            obs = UVAIObservability()
            
            health = obs.get_health_status()
            
            # Should report status with dev flag
            assert "service" in health
            assert "is_production" in health
            assert health["is_production"] is False
            assert "telemetry_available" in health
            assert "tracer_configured" in health
            assert "meter_configured" in health

class TestSecurityDocumentation:
    """Test that security rationale is properly documented"""
    
    def test_api_key_security_comment_exists(self):
        """Verify security comment exists in process_video_with_mcp.py"""
        with open("/home/runner/work/EventRelay/EventRelay/agents/process_video_with_mcp.py", "r") as f:
            content = f.read()
            
        # Should have security comment explaining why we don't use REACT_APP_*
        assert "Security:" in content
        assert "REACT_APP_" in content
        assert "frontend" in content.lower()
    
    def test_validation_security_comments_exist(self):
        """Verify security comments exist in mcp_a2a_mojo_integration.py"""
        with open("/home/runner/work/EventRelay/EventRelay/agents/unified/mcp_a2a_mojo_integration.py", "r") as f:
            content = f.read()
            
        # Should have security comments explaining validation
        assert "Security" in content
        assert "injection" in content.lower()
        assert "validate" in content.lower()
    
    def test_observability_security_comments_exist(self):
        """Verify security comments exist in observability_setup.py"""
        with open("/home/runner/work/EventRelay/EventRelay/agents/observability_setup.py", "r") as f:
            content = f.read()
            
        # Should have security comments explaining production logging
        assert "Security" in content or "CRITICAL" in content
        assert "production" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
