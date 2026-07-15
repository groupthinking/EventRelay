"""Tests for BigQuery export functionality."""

from unittest.mock import patch

from uvai.ml.bigquery_export import _get_bq_client


def test_get_bq_client_import_error() -> None:
    """Test that _get_bq_client returns None when google.cloud.bigquery is missing."""
    with patch.dict("sys.modules", {"google.cloud.bigquery": None}):
        client = _get_bq_client()
        assert client is None
