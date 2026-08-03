"""Executor-isolation regression tests for the three vision providers (#1234).

The providers already read local image bytes off the event loop (#1232/#1233).
That is necessary but not sufficient: the read still lands on the *shared*
default ``ThreadPoolExecutor``, so it shares fate with every other
``asyncio.to_thread`` / ``run_in_executor(None, ...)`` caller in the process
(96 call sites at time of writing, on a pool of ``min(32, cpu + 4)``).

Each test here saturates the **default** executor and then asserts the provider's
local image read still completes. Against the pre-#1234 code these fail with
``TimeoutError`` — the read queues behind unrelated work and never runs. That is
the starvation #1234 describes, expressed as an executable assertion.

Deliberately complementary to the existing ``*_runs_on_worker_thread`` tests:
those pin *where* the read runs, these pin *whose pool it competes for*.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
import types as _types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from youtube_extension.integrations.cloud_ai.base import AnalysisType  # noqa: E402
from youtube_extension.integrations.cloud_ai.providers.aws_rekognition import (  # noqa: E402
    AWSRekognition,
)
from youtube_extension.integrations.cloud_ai.providers.azure_vision import (  # noqa: E402
    AzureVision,
)
from youtube_extension.integrations.cloud_ai.providers.google_cloud import (  # noqa: E402
    GoogleCloudAI,
)
from youtube_extension.utils.blocking_io import reset_blocking_io_executor  # noqa: E402

_TIMEOUT = 5.0
_DEFAULT_POOL_WORKERS = 2

AWS_CONFIG = {
    "aws_access_key_id": "test-access-key-id",
    "aws_secret_access_key": "test-secret-access-key",
    "region": "us-east-1",
}
AZURE_CONFIG = {
    "subscription_key": "test-key-abc",
    "endpoint": "https://eastus.api.cognitive.microsoft.com/",
}
GCP_CONFIG = {"project_id": "my-gcp-project"}


class _DefaultExecutorSaturator:
    """Fills the loop's default executor, leaving zero free workers.

    Shrinking the default pool first makes saturation exact and machine
    independent — otherwise the number of hogs needed depends on ``cpu_count``.
    """

    def __init__(self, loop, workers: int = _DEFAULT_POOL_WORKERS):
        self._loop = loop
        self._workers = workers
        self._previous = getattr(loop, "_default_executor", None)
        self._pool = ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="saturated-default"
        )
        self._entered = threading.Semaphore(0)
        self._release = threading.Event()
        self._tasks: list[asyncio.Task] = []

    def _hog(self) -> None:
        self._entered.release()
        self._release.wait(_TIMEOUT * 3)

    async def __aenter__(self):
        self._loop.set_default_executor(self._pool)
        self._tasks = [
            asyncio.create_task(asyncio.to_thread(self._hog))
            for _ in range(self._workers)
        ]
        # Must yield: a freshly created task does not run until the loop gets
        # control, so a *blocking* acquire here would deadlock the harness
        # before a single hog ever reached the pool.
        deadline = time.monotonic() + _TIMEOUT
        entered = 0
        while entered < self._workers:
            if self._entered.acquire(blocking=False):
                entered += 1
                continue
            assert time.monotonic() < deadline, (
                f"default executor never saturated ({entered}/{self._workers} hogs "
                "started); the harness is broken, not the code under test"
            )
            await asyncio.sleep(0.01)
        return self

    async def __aexit__(self, *exc_info):
        self._release.set()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        if self._previous is None:
            # No default executor existed before us; ``set_default_executor``
            # rejects ``None``, so restore the pristine state directly.
            self._loop._default_executor = None  # noqa: SLF001
        else:
            self._loop.set_default_executor(self._previous)
        self._pool.shutdown(wait=False)
        return False

    async def assert_default_pool_is_blocked(self):
        """Positive control: prove the saturation actually bites.

        Without this, a provider test could pass simply because the pool was
        never really full, and the whole file would be vacuous.
        """
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.to_thread(lambda: "x"), timeout=0.5)


@pytest.fixture(autouse=True)
def _fresh_io_pool():
    reset_blocking_io_executor()
    yield
    reset_blocking_io_executor()


class TestVisionReadsSurviveDefaultExecutorSaturation:
    async def test_aws_local_read_is_not_starved(self, tmp_path):
        image = tmp_path / "frame.jpg"
        image.write_bytes(b"AWS-PAYLOAD")
        provider = AWSRekognition(AWS_CONFIG)

        async with _DefaultExecutorSaturator(asyncio.get_running_loop()) as sat:
            await sat.assert_default_pool_is_blocked()
            result = await asyncio.wait_for(
                provider._prepare_image_input(str(image)), timeout=_TIMEOUT
            )

        assert result == {"Bytes": b"AWS-PAYLOAD"}

    async def test_azure_local_read_is_not_starved(self, tmp_path):
        image = tmp_path / "frame.jpg"
        image.write_bytes(b"AZURE-PAYLOAD")
        provider = AzureVision(AZURE_CONFIG)

        async with _DefaultExecutorSaturator(asyncio.get_running_loop()) as sat:
            await sat.assert_default_pool_is_blocked()
            result = await asyncio.wait_for(
                provider._prepare_image_input(str(image)), timeout=_TIMEOUT
            )

        assert result == b"AZURE-PAYLOAD"

    async def test_google_local_read_is_not_starved(self, tmp_path):
        image = tmp_path / "frame.jpg"
        image.write_bytes(b"GCP-PAYLOAD")
        provider = GoogleCloudAI(GCP_CONFIG)

        image_instance = MagicMock()
        image_instance.source = MagicMock()
        feature_type = MagicMock()
        feature_type.LABEL_DETECTION = "LABEL_DETECTION"
        feature_cls = MagicMock()
        feature_cls.Type = feature_type
        mock_vision = MagicMock()
        mock_vision.Image = MagicMock(return_value=image_instance)
        mock_vision.Feature = feature_cls

        client = AsyncMock()
        client.annotate_image = AsyncMock(
            return_value=MagicMock(
                label_annotations=[],
                localized_object_annotations=[],
                text_annotations=[],
                face_annotations=[],
                safe_search_annotation=None,
                error=MagicMock(message=""),
            )
        )
        provider._vision_client = client

        patched_modules = patch.dict(
            "sys.modules",
            {
                "google": _types.ModuleType("google"),
                "google.cloud": _types.ModuleType("google.cloud"),
                "google.cloud.vision": mock_vision,
            },
        )

        async with _DefaultExecutorSaturator(asyncio.get_running_loop()) as sat:
            await sat.assert_default_pool_is_blocked()
            with patched_modules:
                await asyncio.wait_for(
                    provider.analyze_image(
                        str(image), [AnalysisType.LABEL_DETECTION]
                    ),
                    timeout=_TIMEOUT,
                )

        assert image_instance.content == b"GCP-PAYLOAD"

    async def test_http_url_branch_still_performs_no_disk_read(self, tmp_path):
        """Isolation must not alter URL handling — Azure fetches those itself."""
        provider = AzureVision(AZURE_CONFIG)
        async with _DefaultExecutorSaturator(asyncio.get_running_loop()):
            result = await asyncio.wait_for(
                provider._prepare_image_input("https://example.com/img.jpg"),
                timeout=_TIMEOUT,
            )
        assert result is None

    async def test_missing_file_still_raises_file_not_found(self, tmp_path):
        """Routing through a different executor must not swallow I/O errors."""
        provider = AzureVision(AZURE_CONFIG)
        async with _DefaultExecutorSaturator(asyncio.get_running_loop()):
            with pytest.raises(FileNotFoundError):
                await asyncio.wait_for(
                    provider._prepare_image_input(str(tmp_path / "nope.jpg")),
                    timeout=_TIMEOUT,
                )
