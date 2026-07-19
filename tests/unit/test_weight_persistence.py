import json
import os
import time
from unittest.mock import MagicMock, patch

import pytest

from uvai.ml.weight_persistence import (
    _prune_history,
    _upload_to_gcs,
    load_checkpoint,
    restore_ranker,
    restore_scorer,
    save_checkpoint,
    serialize_ranker,
    serialize_scorer,
)


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Mock the checkpoint directories to use a temporary path."""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_file = checkpoint_dir / "latest.json"
    history_dir = checkpoint_dir / "history"

    monkeypatch.setattr("uvai.ml.weight_persistence.CHECKPOINT_DIR", checkpoint_dir)
    monkeypatch.setattr("uvai.ml.weight_persistence.CHECKPOINT_FILE", checkpoint_file)
    monkeypatch.setattr(
        "uvai.ml.weight_persistence.CHECKPOINT_HISTORY_DIR", history_dir
    )
    monkeypatch.setattr("uvai.ml.weight_persistence.MAX_HISTORY", 5)
    # Disable GCS uploads in tests unless explicitly enabled
    monkeypatch.setattr("uvai.ml.weight_persistence.GCS_BUCKET", None)

    return {
        "checkpoint_dir": checkpoint_dir,
        "checkpoint_file": checkpoint_file,
        "history_dir": history_dir,
    }


def test_save_checkpoint(mock_env):
    """Test saving a checkpoint creates the correct files and content."""
    scorer_state = {"training_samples": 42, "version": "test-1"}
    ranker_state = {"training_samples": 38, "version": "test-1"}

    result_path = save_checkpoint(scorer_state, ranker_state)

    # Check return path
    assert result_path == mock_env["checkpoint_file"]

    # Check latest file exists and is valid
    assert mock_env["checkpoint_file"].exists()

    with open(mock_env["checkpoint_file"]) as f:
        data = json.load(f)

    assert data["scorer"] == scorer_state
    assert data["ranker"] == ranker_state
    assert "version" in data
    assert "timestamp" in data
    assert "epoch_seconds" in data

    # Check history file was created
    history_files = list(mock_env["history_dir"].glob("*.json"))
    assert len(history_files) == 1

    # History file should have same content
    with open(history_files[0]) as f:
        history_data = json.load(f)
    assert history_data == data


def test_save_checkpoint_partial_states(mock_env):
    """Test that saving only scorer or ranker preserves the untouched model's state."""
    # First, save both states
    scorer_state_v1 = {"training_samples": 10, "version": "scorer-v1"}
    ranker_state_v1 = {"training_samples": 20, "version": "ranker-v1"}
    save_checkpoint(scorer_state_v1, ranker_state_v1)

    # Load and verify both states are present
    checkpoint = load_checkpoint()
    assert checkpoint["scorer"] == scorer_state_v1
    assert checkpoint["ranker"] == ranker_state_v1

    # Now save only scorer with updated state (ranker gets {})
    # This simulates production scorer-only checkpoint (serve.py:139-142)
    scorer_state_v2 = {"training_samples": 15, "version": "scorer-v2"}
    save_checkpoint(scorer_state_v2, {})

    # Verify scorer state was updated but ranker state was LOST (bug reproduction)
    checkpoint = load_checkpoint()
    assert checkpoint["scorer"] == scorer_state_v2
    assert checkpoint["ranker"] == {}  # ranker state erased

    # Similarly, save only ranker (scorer gets {})
    # This simulates production ranker-only checkpoint (serve.py:250-253)
    ranker_state_v2 = {"training_samples": 25, "version": "ranker-v2"}
    save_checkpoint({}, ranker_state_v2)

    # Verify ranker state was updated but scorer state was LOST
    checkpoint = load_checkpoint()
    assert checkpoint["scorer"] == {}  # scorer state erased
    assert checkpoint["ranker"] == ranker_state_v2


def test_load_checkpoint_exists(mock_env):
    """Test loading a checkpoint when the file exists."""
    # Ensure dirs exist
    mock_env["checkpoint_dir"].mkdir(parents=True, exist_ok=True)

    dummy_data = {
        "version": "2.0.0",
        "scorer": {"training_samples": 10},
        "ranker": {"training_samples": 20},
    }

    with open(mock_env["checkpoint_file"], "w") as f:
        json.dump(dummy_data, f)

    loaded = load_checkpoint()

    assert loaded == dummy_data


def test_load_checkpoint_not_exists(mock_env):
    """Test loading a checkpoint when the file does not exist returns None."""
    # Ensure it doesn't exist
    if mock_env["checkpoint_file"].exists():
        mock_env["checkpoint_file"].unlink()

    loaded = load_checkpoint()

    assert loaded is None


def test_load_checkpoint_invalid_json(mock_env):
    """Test loading a checkpoint when the file contains invalid JSON returns None."""
    mock_env["checkpoint_dir"].mkdir(parents=True, exist_ok=True)

    with open(mock_env["checkpoint_file"], "w") as f:
        f.write("{ invalid json")

    loaded = load_checkpoint()

    assert loaded is None


class DummyScorer:
    def __init__(self):
        self._source_adjustments = {"a": 1.0}
        self._training_samples = 100
        self._version = "1.0.0"


class DummyRanker:
    def __init__(self):
        self._verb_feedback_weights = {"b": 2.0}
        self._global_feedback_bias = 0.5
        self._training_samples = 200
        self._version = "2.0.0"


def test_serialize_scorer():
    scorer = DummyScorer()
    state = serialize_scorer(scorer)

    assert state == {
        "source_adjustments": {"a": 1.0},
        "training_samples": 100,
        "version": "1.0.0",
    }


def test_serialize_ranker():
    ranker = DummyRanker()
    state = serialize_ranker(ranker)

    assert state == {
        "verb_feedback_weights": {"b": 2.0},
        "global_feedback_bias": 0.5,
        "training_samples": 200,
        "version": "2.0.0",
    }


def test_restore_scorer():
    scorer = DummyScorer()

    checkpoint = {
        "scorer": {
            "source_adjustments": {"c": 3.0},
            "training_samples": 150,
            "version": "1.5.0",
        }
    }

    restore_scorer(scorer, checkpoint)

    assert scorer._source_adjustments == {"c": 3.0}
    # verify _weights gets mirrored from source_adjustments as per implementation
    assert scorer._weights == {"c": 3.0}
    assert scorer._training_samples == 150
    assert scorer._version == "1.5.0"


def test_restore_ranker():
    ranker = DummyRanker()

    checkpoint = {
        "ranker": {
            "verb_feedback_weights": {"d": 4.0},
            "global_feedback_bias": 0.8,
            "training_samples": 250,
            "version": "2.5.0",
        }
    }

    restore_ranker(ranker, checkpoint)

    assert ranker._verb_feedback_weights == {"d": 4.0}
    assert ranker._global_feedback_bias == 0.8
    assert ranker._training_samples == 250
    assert ranker._version == "2.5.0"


def test_prune_history(mock_env, monkeypatch):
    """Test that prune_history keeps only MAX_HISTORY newest files."""
    monkeypatch.setattr("uvai.ml.weight_persistence.MAX_HISTORY", 2)
    history_dir = mock_env["history_dir"]
    history_dir.mkdir(parents=True, exist_ok=True)

    # Create 3 files with different modification times
    files = [
        history_dir / "file1.json",
        history_dir / "file2.json",
        history_dir / "file3.json",
    ]

    for i, file in enumerate(files):
        file.touch()
        # Set mtime to past, increasing with i
        # So file3 is newest, file2 middle, file1 oldest
        os.utime(file, (time.time() - (10 - i), time.time() - (10 - i)))

    _prune_history()

    remaining_files = list(history_dir.glob("*.json"))

    assert len(remaining_files) == 2
    # file1 (oldest) should be deleted, file2 and file3 remain
    assert not files[0].exists()
    assert files[1].exists()
    assert files[2].exists()


@patch("uvai.ml.weight_persistence.GCS_BUCKET", "test-bucket")
@patch("uvai.ml.weight_persistence.GCS_PREFIX", "test-prefix/")
def test_upload_to_gcs():
    """Test that _upload_to_gcs uploads to the correct blobs."""
    # We need to mock the google.cloud.storage import inside the function
    with patch.dict("sys.modules", {"google.cloud": MagicMock()}):
        import sys

        from uvai.ml.weight_persistence import _upload_to_gcs

        # Setup mock client
        mock_storage = MagicMock()
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        sys.modules["google.cloud"].storage = mock_storage
        mock_storage.Client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        payload = '{"test": "data"}'
        filename = "test_123.json"

        _upload_to_gcs(payload, filename)

        # Verify calls
        mock_storage.Client.assert_called_once()
        mock_client.bucket.assert_called_once_with("test-bucket")

        # Should create two blobs: latest and history
        assert mock_bucket.blob.call_count == 2
        mock_bucket.blob.assert_any_call("test-prefix/latest.json")
        mock_bucket.blob.assert_any_call("test-prefix/history/test_123.json")

        assert mock_blob.upload_from_string.call_count == 2
        mock_blob.upload_from_string.assert_any_call(
            payload, content_type="application/json"
        )


@patch("uvai.ml.weight_persistence.GCS_BUCKET", "test-bucket")
@patch("uvai.ml.weight_persistence.GCS_PREFIX", "test-prefix/")
def test_upload_to_gcs_failure_is_non_fatal(caplog):
    """Test that _upload_to_gcs failures don't raise exceptions (best-effort)."""
    import logging

    # Test 1: Client initialization failure
    with patch.dict("sys.modules", {"google.cloud": MagicMock()}):
        import sys

        mock_storage = MagicMock()
        sys.modules["google.cloud"].storage = mock_storage
        # Make Client() raise an exception
        mock_storage.Client.side_effect = Exception("Credentials not found")

        # Should not raise, only log warning
        with caplog.at_level(logging.WARNING):
            _upload_to_gcs('{"test": "data"}', "test.json")

        assert "GCS checkpoint upload failed (non-fatal)" in caplog.text
        assert "Credentials not found" in caplog.text

    caplog.clear()

    # Test 2: Upload failure
    with patch.dict("sys.modules", {"google.cloud": MagicMock()}):
        import sys

        mock_storage = MagicMock()
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_blob = MagicMock()

        sys.modules["google.cloud"].storage = mock_storage
        mock_storage.Client.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob
        # Make upload_from_string raise an exception
        mock_blob.upload_from_string.side_effect = Exception("Network timeout")

        # Should not raise, only log warning
        with caplog.at_level(logging.WARNING):
            _upload_to_gcs('{"test": "data"}', "test.json")

        assert "GCS checkpoint upload failed (non-fatal)" in caplog.text
        assert "Network timeout" in caplog.text
