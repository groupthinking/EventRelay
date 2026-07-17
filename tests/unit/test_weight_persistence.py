import json
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from uvai.ml.weight_persistence import save_checkpoint


@pytest.fixture
def mock_dirs(tmp_path):
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_file = checkpoint_dir / "latest.json"
    history_dir = checkpoint_dir / "history"

    with patch("uvai.ml.weight_persistence.CHECKPOINT_DIR", checkpoint_dir), \
         patch("uvai.ml.weight_persistence.CHECKPOINT_FILE", checkpoint_file), \
         patch("uvai.ml.weight_persistence.CHECKPOINT_HISTORY_DIR", history_dir):
        yield {
            "checkpoint_dir": checkpoint_dir,
            "checkpoint_file": checkpoint_file,
            "history_dir": history_dir
        }


def test_save_checkpoint_success(mock_dirs):
    scorer_state = {"training_samples": 42, "version": "1.1.0"}
    ranker_state = {"training_samples": 38, "version": "1.1.0"}

    with patch("uvai.ml.weight_persistence._prune_history") as mock_prune, \
         patch("uvai.ml.weight_persistence._upload_to_gcs") as mock_upload, \
         patch("uvai.ml.weight_persistence.GCS_BUCKET", None):

        result_path = save_checkpoint(scorer_state, ranker_state)

        assert result_path == mock_dirs["checkpoint_file"]
        assert result_path.exists()

        # Check content of latest.json
        saved_data = json.loads(result_path.read_text())
        assert saved_data["version"] == "2.0.0"
        assert "timestamp" in saved_data
        assert "epoch_seconds" in saved_data
        assert saved_data["scorer"] == scorer_state
        assert saved_data["ranker"] == ranker_state

        # Check history file
        history_files = list(mock_dirs["history_dir"].glob("*.json"))
        assert len(history_files) == 1
        history_data = json.loads(history_files[0].read_text())
        assert history_data == saved_data

        mock_prune.assert_called_once()
        mock_upload.assert_not_called()


def test_save_checkpoint_with_gcs(mock_dirs):
    scorer_state = {"training_samples": 10}
    ranker_state = {"training_samples": 10}

    with patch("uvai.ml.weight_persistence._prune_history") as mock_prune, \
         patch("uvai.ml.weight_persistence._upload_to_gcs") as mock_upload, \
         patch("uvai.ml.weight_persistence.GCS_BUCKET", "my-bucket"):

        save_checkpoint(scorer_state, ranker_state)

        mock_prune.assert_called_once()
        mock_upload.assert_called_once()
        args, _ = mock_upload.call_args
        payload = args[0]
        ts_name = args[1]

        assert isinstance(payload, str)
        assert ts_name.endswith(".json")

        # Verify payload is valid JSON
        payload_data = json.loads(payload)
        assert payload_data["scorer"] == scorer_state
        assert payload_data["ranker"] == ranker_state
