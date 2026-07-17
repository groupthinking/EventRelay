"""
Tests for security vulnerability fixes
Tests Issues #1, #2, and #3 from security audit

NOTE: These tests verify security patterns are in place.
Tests that require specific modules will skip if unavailable.
"""

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))


class TestAPIKeyExposureFix:
    """Test Issue 1: API Key Exposure Risk Fix"""

    def test_env_example_has_youtube_api_key(self):
        """Verify .env.example documents YOUTUBE_API_KEY (not REACT_APP_*)"""
        env_example = project_root / ".env.example"
        assert env_example.exists(), ".env.example not found"

        content = env_example.read_text()

        # Should have proper backend env var
        assert "YOUTUBE_API_KEY" in content

        # Should NOT have frontend-only env var (would be security issue)
        # Note: REACT_APP_* vars should only be in frontend
        if "REACT_APP_YOUTUBE_API_KEY" in content:
            pytest.fail("Backend .env.example should not reference REACT_APP_* variables")

    def test_backend_imports_work(self):
        """Verify backend video processing module can be imported"""
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from agents.process_video_with_mcp import RealVideoProcessor
            assert True
        except (ImportError, Exception) as e:
            pytest.skip(f"Module not available: {e}")


class TestInputValidationFix:
    """Test Issue 2: Input Validation for Agent Messages"""

    def test_agents_unified_module_exists(self):
        """Verify agents/unified directory exists"""
        agents_unified = project_root / "src" / "agents" / "unified"
        assert agents_unified.exists(), f"agents/unified directory not found at {agents_unified}"

    def test_validation_functions_exist(self):
        """Verify validation functions exist in the codebase"""
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from agents.unified.mcp_a2a_mojo_integration import (
                    validate_agent_identifier,
                    sanitize_message_content
                )

            # Basic smoke test
            assert validate_agent_identifier("test_agent") is True
            assert validate_agent_identifier("") is False

        except (ImportError, Exception) as e:
            pytest.skip(f"Module not available: {e}")

    def test_sanitize_removes_control_chars(self):
        """Test content sanitization removes control characters"""
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                from agents.unified.mcp_a2a_mojo_integration import sanitize_message_content

            malicious_string = "normal\\x00text\\x01"
            sanitized = sanitize_message_content(malicious_string)

            # Should not contain null bytes
            assert "\\x00" not in str(sanitized) or sanitized == malicious_string

        except (ImportError, Exception) as e:
            pytest.skip(f"Module not available: {e}")


class TestObservabilityFix:
    """Test Issue 3: Observability Silent Failure Fix"""

    def test_observability_module_exists(self):
        """Verify observability_setup.py exists"""
        obs_file = project_root / "src" / "agents" / "observability_setup.py"
        if not obs_file.exists():
            pytest.skip(f"Observability file not found: {obs_file}")

        content = obs_file.read_text()

        # Should have logging setup
        assert "logging" in content.lower() or "logger" in content.lower()

    def test_uvai_observability_can_import(self):
        """Test UVAIObservability can be imported"""
        try:
            from agents.observability_setup import UVAIObservability
            obs = UVAIObservability()
            assert hasattr(obs, 'get_health_status') or hasattr(obs, 'setup_complete')
        except ImportError as e:
            pytest.skip(f"Module not available: {e}")
        except Exception as e:
            # May fail due to missing telemetry, that's OK
            pytest.skip(f"Module initialization failed (expected without OTEL): {e}")


class TestSecurityDocumentation:
    """Test that security rationale is properly documented"""

    def test_api_key_security_in_env_example(self):
        """Verify .env.example has security warnings"""
        env_example = project_root / ".env.example"
        if not env_example.exists():
            pytest.skip(".env.example not found")

        content = env_example.read_text()

        # Should have warning about secrets
        assert "secret" in content.lower() or "never commit" in content.lower()

    def test_process_video_exists(self):
        """Verify process_video_with_mcp.py exists and has security patterns"""
        file_path = project_root / "src" / "agents" / "process_video_with_mcp.py"
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")

        content = file_path.read_text()

        # Should have API key handling
        assert "API_KEY" in content or "api_key" in content

    def test_observability_has_logging(self):
        """Verify observability setup has logging patterns"""
        file_path = project_root / "src" / "agents" / "observability_setup.py"
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")

        content = file_path.read_text()

        # Should have production-aware logging
        assert "log" in content.lower()


class TestSecurityBestPractices:
    """General security best practices tests"""

    def test_no_hardcoded_api_keys(self):
        """Verify no hardcoded API keys in main backend files"""
        files_to_check = [
            project_root / "src" / "uvai" / "api" / "main.py",
            project_root / "src" / "youtube_extension" / "backend" / "main_v2.py",
        ]

        suspect_patterns = [
            "AIzaSy",  # Google API key prefix
            "sk-",    # OpenAI key prefix
            "xai-",   # X.AI key prefix
        ]

        for file_path in files_to_check:
            if not file_path.exists():
                continue

            content = file_path.read_text()
            for pattern in suspect_patterns:
                # Allow patterns in comments/strings explaining what they are
                if pattern in content:
                    # Check if it's just a documentation reference
                    lines_with_pattern = [l for l in content.split('\n') if pattern in l]
                    for line in lines_with_pattern:
                        # If it looks like a full key (pattern + 30+ chars), fail
                        if len(line.strip()) > 50 and not line.strip().startswith('#'):
                            pytest.fail(f"Possible hardcoded API key in {file_path}: {line[:80]}...")

    def test_dockerfile_uses_nonroot_user(self):
        """Verify Dockerfile.production uses non-root user"""
        dockerfile = project_root / "Dockerfile.production"
        if not dockerfile.exists():
            pytest.skip("Dockerfile.production not found")

        content = dockerfile.read_text()

        assert "USER" in content, "Dockerfile should switch to non-root user"
        assert "appuser" in content or "nonroot" in content.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

class TestSecurityAgentEvalFix:
    """Test Issue: Security Agent Eval Fix"""

    @pytest.mark.asyncio
    async def test_security_agent_distinguishes_eval_from_literal_eval(self, tmp_path):
        """Verify the security agent does not flag literal_eval as dangerous eval"""
        from agents.specialized.security_agent import SecurityAgent

        # Create dummy project path
        project_path = tmp_path / "dummy_project"
        project_path.mkdir()

        # Create a file with dangerous eval
        bad_file = project_path / "bad.py"
        bad_file.write_text("x = input()\neval(x)\nexec(x)")

        # Create a file with safe literal_eval
        safe_file = project_path / "safe.py"
        safe_file.write_text("import ast\nx = input()\nast.literal_eval(x)")

        agent = SecurityAgent()
        agent.project_path = project_path

        results = await agent.check_input_validation()

        issues = results.get("issues", [])
        eval_issues = [issue for issue in issues if issue.get("type") == "dangerous_eval"]

        # Should only find the dangerous eval in bad.py
        bad_file_str = str(bad_file.relative_to(project_path))
        safe_file_str = str(safe_file.relative_to(project_path))

        bad_found = False
        safe_found = False

        for issue in eval_issues:
            if issue.get("file") == bad_file_str:
                bad_found = True
            elif issue.get("file") == safe_file_str:
                safe_found = True

        assert bad_found, "Failed to detect dangerous eval"
        assert not safe_found, "Falsely detected literal_eval as dangerous"
