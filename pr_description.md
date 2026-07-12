🎯 **What:** Added missing unit tests for the BigQuery Export module (`src/uvai/ml/bigquery_export.py`) and refactored the function signature for `export_transcript_outcome` to correctly accept an `outcome` dictionary instead of positional keyword arguments.

📊 **Coverage:** The new test suite (`tests/unit/test_bigquery_export.py`) covers happy paths, edge cases, error conditions, and the fallback REST API logic for the following functions:
- `_insert_rows`
- `_insert_via_rest`
- `export_transcript_outcome`
- `export_action_feedback`
- `export_model_checkpoint`
- `export_pipeline_run`

✨ **Result:** Increased test coverage ensuring that the ML model training data correctly falls back to REST API insertion when the BigQuery client is unavailable, and prevents regressions when modifying these core export mechanisms.
