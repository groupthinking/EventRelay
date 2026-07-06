"""Unit tests for eventrelay_sdk.types.

Scope: only the ``error_reason`` field recently added to
``VideoJobStatusResponse`` (mirrors the same field on the backend's
``youtube_extension.backend.api.v1.models.VideoJobStatusResponse``).
"""

from __future__ import annotations

import sys
from pathlib import Path

# The SDK is a standalone, not-yet-installed package, so make it importable
# without requiring `pip install -e .`.
_SDK_ROOT = Path(__file__).resolve().parents[1]
if str(_SDK_ROOT) not in sys.path:
    sys.path.insert(0, str(_SDK_ROOT))

import pytest
from pydantic import ValidationError

from eventrelay_sdk.types import JobStatus, VideoJobStatusResponse


class TestVideoJobStatusResponseErrorReason:
    def test_error_reason_defaults_to_none(self):
        status = VideoJobStatusResponse(job_id="job_1", status=JobStatus.pending)
        assert status.error_reason is None

    def test_error_reason_accepts_slug(self):
        status = VideoJobStatusResponse(
            job_id="job_2",
            status=JobStatus.failed,
            error="Gemini timed out",
            error_reason="gemini_api_timeout",
        )
        assert status.error_reason == "gemini_api_timeout"

    def test_error_reason_independent_of_error_message(self):
        """error_reason is a separate, optional slug from the free-text error message."""
        status = VideoJobStatusResponse(
            job_id="job_3",
            status=JobStatus.failed,
            error="Human readable failure text",
        )
        assert status.error == "Human readable failure text"
        assert status.error_reason is None

    def test_error_reason_included_in_model_dump(self):
        status = VideoJobStatusResponse(
            job_id="job_4",
            status=JobStatus.failed,
            error_reason="youtube_download_failed",
        )
        dumped = status.model_dump()
        assert dumped["error_reason"] == "youtube_download_failed"

    def test_error_reason_round_trips_through_json(self):
        status = VideoJobStatusResponse(
            job_id="job_5",
            status=JobStatus.failed,
            error_reason="transcript_not_found",
        )
        rehydrated = VideoJobStatusResponse.model_validate_json(status.model_dump_json())
        assert rehydrated.error_reason == "transcript_not_found"

    def test_error_reason_omitted_when_not_provided(self):
        """Existing payloads without error_reason should still validate (backward-compatible)."""
        status = VideoJobStatusResponse.model_validate(
            {"job_id": "job_6", "status": "complete", "progress": 100.0}
        )
        assert status.error_reason is None

    def test_error_reason_rejects_non_string_values(self):
        with pytest.raises(ValidationError):
            VideoJobStatusResponse(
                job_id="job_7",
                status=JobStatus.failed,
                error_reason={"not": "a string"},
            )