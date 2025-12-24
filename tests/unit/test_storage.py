"""
Storage Tests - Basic functionality for file operations and data persistence.
"""
import os
import tempfile
import pytest
from pathlib import Path


class TestStorage:
    """Test storage functionality."""

    def test_storage_directory_creation(self):
        """Test creating storage directories."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_path = Path(tmp_dir) / "storage" / "videos"
            storage_path.mkdir(parents=True, exist_ok=True)
            assert storage_path.exists()
            assert storage_path.is_dir()

    def test_file_write_read(self):
        """Test basic file write and read operations."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_file = Path(tmp_dir) / "test_file.txt"
            test_content = "Test content for storage validation"

            # Write file
            test_file.write_text(test_content)
            assert test_file.exists()

            # Read file
            read_content = test_file.read_text()
            assert read_content == test_content

    def test_json_storage(self):
        """Test JSON storage functionality."""
        import json
        with tempfile.TemporaryDirectory() as tmp_dir:
            json_file = Path(tmp_dir) / "test_data.json"
            test_data = {
                "video_id": "auJzb1D-fag",
                "title": "Test Video",
                "processed": True,
                "metadata": {
                    "duration": 120,
                    "format": "mp4"
                }
            }

            # Write JSON
            json_file.write_text(json.dumps(test_data, indent=2))
            assert json_file.exists()

            # Read JSON
            loaded_data = json.loads(json_file.read_text())
            assert loaded_data == test_data
            assert loaded_data["video_id"] == "auJzb1D-fag"

    def test_storage_cleanup(self):
        """Test storage cleanup functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test files
            test_files = []
            for i in range(3):
                test_file = Path(tmp_dir) / f"file_{i}.txt"
                test_file.write_text(f"Content {i}")
                test_files.append(test_file)

            # Verify files exist
            for test_file in test_files:
                assert test_file.exists()

            # Cleanup (remove files)
            for test_file in test_files:
                test_file.unlink()
                assert not test_file.exists()


class TestStorageEdgeCases:
    """Test storage edge cases and error conditions."""

    def test_invalid_path_handling(self):
        """Test handling of invalid paths."""
        invalid_path = Path("/invalid/nonexistent/path/file.txt")

        # Should handle gracefully without crashing
        try:
            invalid_path.read_text()
        except FileNotFoundError:
            # Expected behavior
            pass
        except PermissionError:
            # Also acceptable
            pass

    def test_large_file_handling(self):
        """Test handling of large files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            large_file = Path(tmp_dir) / "large_file.txt"

            # Create a moderately large content (1MB)
            large_content = "A" * (1024 * 1024)  # 1MB of 'A' characters
            large_file.write_text(large_content)

            assert large_file.exists()
            assert large_file.stat().st_size > 1000000  # > 1MB

            # Verify we can read it back
            read_content = large_file.read_text()
            assert len(read_content) == len(large_content)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])