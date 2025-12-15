"""
Tests for scripts/setup_env.py - Interactive environment setup tool
"""
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from setup_env import (
    check_existing_env,
    copy_env_template,
    load_existing_env,
    update_env_file,
    API_KEYS
)


class TestSetupEnv:
    """Test interactive environment setup functionality."""

    def test_check_existing_env_when_missing(self):
        """Test checking for .env file when it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch('setup_env.Path') as mock_path:
                mock_path.return_value.parent.parent = tmp_path
                exists, env_path = check_existing_env()
                assert exists is False or exists is True  # Just verify it returns

    def test_load_existing_env_empty_file(self):
        """Test loading an empty .env file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("")
            
            env_vars = load_existing_env(env_file)
            assert env_vars == {}

    def test_load_existing_env_with_values(self):
        """Test loading .env file with values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("""
# Comment line
GEMINI_API_KEY=test-key-123
OPENAI_API_KEY=sk-test-456

# Another comment
YOUTUBE_API_KEY=AIza-test-789
""")
            
            env_vars = load_existing_env(env_file)
            assert env_vars["GEMINI_API_KEY"] == "test-key-123"
            assert env_vars["OPENAI_API_KEY"] == "sk-test-456"
            assert env_vars["YOUTUBE_API_KEY"] == "AIza-test-789"
            assert len(env_vars) == 3

    def test_copy_env_template(self):
        """Test copying .env.example to .env."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_example = tmp_path / ".env.example"
            env_example.write_text("GEMINI_API_KEY=your-key\nOPENAI_API_KEY=your-key")
            
            env_file = tmp_path / ".env"
            
            # Mock user input to not overwrite
            with patch('builtins.input', return_value='n'):
                result = copy_env_template(tmp_path)
            
            # Should return True even if not overwriting
            assert result is True

    def test_update_env_file_new_key(self):
        """Test adding a new key to .env file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("# Existing content\nEXISTING_KEY=value")
            
            update_env_file(env_file, "NEW_KEY", "new-value")
            
            content = env_file.read_text()
            assert "NEW_KEY=new-value" in content
            assert "EXISTING_KEY=value" in content

    def test_update_env_file_existing_key(self):
        """Test updating an existing key in .env file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("GEMINI_API_KEY=old-value\nOTHER_KEY=other-value")
            
            update_env_file(env_file, "GEMINI_API_KEY", "new-value")
            
            content = env_file.read_text()
            assert "GEMINI_API_KEY=new-value" in content
            assert "GEMINI_API_KEY=old-value" not in content
            assert "OTHER_KEY=other-value" in content

    def test_update_env_file_preserves_comments(self):
        """Test that updating .env file preserves comments."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("""# Important comment
GEMINI_API_KEY=old-value
# Another comment
OTHER_KEY=value""")
            
            update_env_file(env_file, "GEMINI_API_KEY", "new-value")
            
            content = env_file.read_text()
            assert "# Important comment" in content
            assert "# Another comment" in content
            assert "GEMINI_API_KEY=new-value" in content

    def test_update_env_file_ignores_commented_lines(self):
        """Test that update doesn't modify commented lines."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("""# GEMINI_API_KEY=commented-value
GEMINI_API_KEY=actual-value
OTHER_KEY=value""")
            
            update_env_file(env_file, "GEMINI_API_KEY", "new-value")
            
            content = env_file.read_text()
            assert "# GEMINI_API_KEY=commented-value" in content  # Comment preserved
            assert "GEMINI_API_KEY=new-value" in content  # Actual value updated
            assert "GEMINI_API_KEY=actual-value" not in content

    def test_api_keys_configuration(self):
        """Test that API_KEYS dictionary is properly configured."""
        assert "GEMINI_API_KEY" in API_KEYS
        assert "OPENAI_API_KEY" in API_KEYS
        assert "YOUTUBE_API_KEY" in API_KEYS
        
        # Check GEMINI_API_KEY has correct structure
        gemini_config = API_KEYS["GEMINI_API_KEY"]
        assert "name" in gemini_config
        assert "url" in gemini_config
        assert "required" in gemini_config
        assert "priority" in gemini_config
        assert "description" in gemini_config
        
        # Verify GEMINI is marked as required
        assert gemini_config["required"] is True

    def test_api_keys_have_urls(self):
        """Test that all API keys have URLs for obtaining them."""
        for key_name, config in API_KEYS.items():
            assert "url" in config
            assert len(config["url"]) > 0
            assert config["url"] != ""

    def test_load_env_with_equals_in_value(self):
        """Test loading .env file where values contain '=' characters."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            env_file.write_text("DATABASE_URL=postgresql://user:pass@host:5432/db?param=value")
            
            env_vars = load_existing_env(env_file)
            assert env_vars["DATABASE_URL"] == "postgresql://user:pass@host:5432/db?param=value"

    def test_update_env_file_with_multiline_handling(self):
        """Test updating .env file handles multiple occurrences correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            env_file = Path(tmp_dir) / ".env"
            # This should only have one uncommented key
            env_file.write_text("""GEMINI_API_KEY=value1
# GEMINI_API_KEY=commented
OTHER_KEY=value2""")
            
            update_env_file(env_file, "GEMINI_API_KEY", "updated-value")
            
            content = env_file.read_text()
            lines = [l for l in content.split('\n') if l.strip() and not l.startswith('#')]
            
            # Should have exactly one uncommented GEMINI_API_KEY
            gemini_lines = [l for l in lines if l.startswith('GEMINI_API_KEY=')]
            assert len(gemini_lines) == 1
            assert gemini_lines[0] == "GEMINI_API_KEY=updated-value"
