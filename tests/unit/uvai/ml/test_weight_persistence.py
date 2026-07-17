"""Tests for weight persistence restoring logic."""

from unittest.mock import patch

from uvai.ml.weight_persistence import restore_ranker


class DummyRanker:
    def __init__(self):
        self._verb_feedback_weights = {}
        self._global_feedback_bias = 0.0
        self._training_samples = 0
        self._version = "0.0.0"


def test_restore_ranker_no_state():
    """Test restoring ranker when checkpoint has no ranker state."""
    ranker = DummyRanker()
    checkpoint = {}

    restore_ranker(ranker, checkpoint)

    assert ranker._verb_feedback_weights == {}
    assert ranker._global_feedback_bias == 0.0
    assert ranker._training_samples == 0
    assert ranker._version == "0.0.0"


def test_restore_ranker_with_full_state():
    """Test restoring ranker with a complete state."""
    ranker = DummyRanker()
    checkpoint = {
        "ranker": {
            "verb_feedback_weights": {"analyze": 1.5, "review": 0.5},
            "global_feedback_bias": 1.25,
            "training_samples": 42,
            "version": "1.2.3",
        }
    }

    with patch("uvai.ml.weight_persistence.logger.info") as mock_logger:
        restore_ranker(ranker, checkpoint)

        assert ranker._verb_feedback_weights == {"analyze": 1.5, "review": 0.5}
        assert ranker._global_feedback_bias == 1.25
        assert ranker._training_samples == 42
        assert ranker._version == "1.2.3"

        mock_logger.assert_called_once_with(
            "Restored ranker: %d training samples, version=%s",
            42,
            "1.2.3",
        )


def test_restore_ranker_partial_state():
    """Test restoring ranker with a partial state."""
    ranker = DummyRanker()
    checkpoint = {
        "ranker": {
            "verb_feedback_weights": {"test": 2.0},
        }
    }

    with patch("uvai.ml.weight_persistence.logger.info") as mock_logger:
        restore_ranker(ranker, checkpoint)

        assert ranker._verb_feedback_weights == {"test": 2.0}
        assert ranker._global_feedback_bias == 0.0
        assert ranker._training_samples == 0
        assert ranker._version == "0.0.0"

        mock_logger.assert_called_once_with(
            "Restored ranker: %d training samples, version=%s",
            0,
            "0.0.0",
        )
