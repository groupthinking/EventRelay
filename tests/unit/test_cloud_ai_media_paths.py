"""Security tests for the cloud AI local media path guard.

Covers the acceptance criteria of issue #1209: a caller-supplied ``image_url``
must not be able to read arbitrary files off the host via an absolute path,
``../`` traversal, or a symlink that escapes the permitted root.
"""

from __future__ import annotations

import os
import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

from youtube_extension.integrations.cloud_ai.base import AnalysisType
from youtube_extension.integrations.cloud_ai.exceptions import (
    CloudAIError,
    ConfigurationError,
    UnsafeMediaPathError,
)
from youtube_extension.integrations.cloud_ai.media_paths import (
    MEDIA_ROOT_ENV_VAR,
    get_media_root,
    resolve_local_media_path,
)
from youtube_extension.integrations.cloud_ai.providers.aws_rekognition import (
    AWSRekognition,
)
from youtube_extension.integrations.cloud_ai.providers.azure_vision import AzureVision
from youtube_extension.integrations.cloud_ai.providers.google_cloud import GoogleCloudAI

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

AWS_CONFIG = {
    "aws_access_key_id": "test-access-key-id",
    "aws_secret_access_key": "test-secret-access-key",
    "region": "us-east-1",
}

AZURE_CONFIG = {
    "subscription_key": "test-key-abc",
    "endpoint": "https://eastus.api.cognitive.microsoft.com/",
}

GOOGLE_CONFIG = {"project_id": "test-project"}


@pytest.fixture
def media_root(tmp_path, monkeypatch):
    """A configured media root containing one legitimate image."""
    root = tmp_path / "media"
    root.mkdir()
    (root / "photo.jpg").write_bytes(b"\xff\xd8\xff\xe0")
    monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, str(root))
    return root


@pytest.fixture
def secret_file(tmp_path):
    """A file that lives outside any media root -- the exfiltration target."""
    secret = tmp_path / "secrets.env"
    secret.write_text("API_KEY=super-secret")
    return secret


# ===========================================================================
# get_media_root
# ===========================================================================


class TestGetMediaRoot:
    def test_unset_returns_none(self, monkeypatch):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        assert get_media_root() is None

    def test_empty_string_returns_none(self, monkeypatch):
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, "")
        assert get_media_root() is None

    def test_whitespace_only_returns_none(self, monkeypatch):
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, "   ")
        assert get_media_root() is None

    def test_returns_resolved_absolute_path(self, tmp_path, monkeypatch):
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, str(tmp_path))
        root = get_media_root()
        assert root == tmp_path.resolve()
        assert root.is_absolute()

    def test_relative_value_is_made_absolute(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "assets").mkdir()
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, "assets")
        assert get_media_root() == (tmp_path / "assets").resolve()

    def test_surrounding_whitespace_is_stripped(self, tmp_path, monkeypatch):
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, f"  {tmp_path}  ")
        assert get_media_root() == tmp_path.resolve()

    def test_unresolvable_value_raises_configuration_error(self, monkeypatch):
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, "/whatever")
        with patch(
            "youtube_extension.integrations.cloud_ai.media_paths.Path.resolve",
            side_effect=OSError("boom"),
        ):
            with pytest.raises(ConfigurationError) as exc_info:
                get_media_root()
        assert exc_info.value.missing_config == MEDIA_ROOT_ENV_VAR

    def test_root_pointing_at_a_file_raises_configuration_error(
        self, tmp_path, monkeypatch
    ):
        """A regular file as the root (e.g. ``/etc/passwd``) must be refused.

        Without the directory check ``is_relative_to`` treats the file as being
        "inside" itself, so the misconfiguration would silently allow reading
        exactly that one file -- a fail-closed violation.
        """
        target = tmp_path / "passwd"
        target.write_text("root:x:0:0:")
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, str(target))
        with pytest.raises(ConfigurationError) as exc_info:
            get_media_root()
        assert exc_info.value.missing_config == MEDIA_ROOT_ENV_VAR

    def test_nonexistent_root_raises_configuration_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, str(tmp_path / "does-not-exist"))
        with pytest.raises(ConfigurationError):
            get_media_root()

    def test_resolve_rejects_file_root_end_to_end(self, tmp_path, monkeypatch):
        """The misconfiguration must surface through ``resolve_local_media_path``."""
        target = tmp_path / "passwd"
        target.write_text("root:x:0:0:")
        monkeypatch.setenv(MEDIA_ROOT_ENV_VAR, str(target))
        with pytest.raises(ConfigurationError):
            resolve_local_media_path(str(target))


# ===========================================================================
# resolve_local_media_path
# ===========================================================================


class TestResolveLocalMediaPathDisabled:
    """With no root configured, every local path must be refused."""

    def test_local_reads_disabled_by_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        existing = tmp_path / "photo.jpg"
        existing.write_bytes(b"data")
        with pytest.raises(UnsafeMediaPathError) as exc_info:
            resolve_local_media_path(str(existing))
        assert "disabled" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "UNSAFE_MEDIA_PATH"

    def test_disabled_error_names_the_env_var(self, monkeypatch):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        with pytest.raises(UnsafeMediaPathError) as exc_info:
            resolve_local_media_path("/etc/passwd")
        assert MEDIA_ROOT_ENV_VAR in str(exc_info.value)


class TestResolveLocalMediaPathRejections:
    def test_absolute_path_outside_root_is_rejected(self, media_root, secret_file):
        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path(str(secret_file))

    def test_etc_passwd_is_rejected(self, media_root):
        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path("/etc/passwd")

    def test_dotdot_traversal_is_rejected(self, media_root, secret_file):
        traversal = str(media_root / ".." / "secrets.env")
        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path(traversal)

    def test_deep_dotdot_traversal_is_rejected(self, media_root):
        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path(
                str(media_root / ".." / ".." / ".." / "etc" / "passwd")
            )

    def test_symlink_escaping_root_is_rejected(self, media_root, secret_file):
        """A symlink *inside* the root pointing outside it must not slip through.

        This is the case a purely lexical ``..`` check would miss.
        """
        link = media_root / "innocent.jpg"
        link.symlink_to(secret_file)
        # Sanity: the link really does read the secret without the guard.
        assert link.read_text() == "API_KEY=super-secret"

        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path(str(link))

    def test_symlinked_directory_escape_is_rejected(self, media_root, tmp_path):
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "loot.txt").write_text("loot")
        (media_root / "shortcut").symlink_to(outside_dir, target_is_directory=True)

        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path(str(media_root / "shortcut" / "loot.txt"))

    def test_sibling_directory_prefix_is_rejected(self, media_root, tmp_path):
        """``/tmp/media-evil`` must not pass a check against ``/tmp/media``."""
        sibling = tmp_path / "media-evil"
        sibling.mkdir()
        target = sibling / "photo.jpg"
        target.write_bytes(b"nope")

        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path(str(target))

    def test_empty_path_is_rejected(self, media_root):
        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path("")

    def test_whitespace_path_is_rejected(self, media_root):
        with pytest.raises(UnsafeMediaPathError):
            resolve_local_media_path("   ")

    def test_directory_inside_root_is_rejected(self, media_root):
        subdir = media_root / "album"
        subdir.mkdir()
        with pytest.raises(UnsafeMediaPathError) as exc_info:
            resolve_local_media_path(str(subdir))
        assert "regular file" in str(exc_info.value)

    def test_fifo_inside_root_is_rejected(self, media_root):
        """A FIFO would block a worker thread forever on read."""
        fifo = media_root / "pipe.jpg"
        try:
            os.mkfifo(fifo)
        except (AttributeError, NotImplementedError, OSError):
            pytest.skip("mkfifo unavailable on this platform")
        with pytest.raises(UnsafeMediaPathError) as exc_info:
            resolve_local_media_path(str(fifo))
        assert "regular file" in str(exc_info.value)

    def test_error_does_not_leak_resolved_server_path(self, media_root, secret_file):
        with pytest.raises(UnsafeMediaPathError) as exc_info:
            resolve_local_media_path(str(secret_file))
        # The message must not echo the resolved filesystem location.
        assert str(secret_file.resolve()) not in str(exc_info.value)

    def test_error_carries_provider_and_requested_path(self, media_root):
        with pytest.raises(UnsafeMediaPathError) as exc_info:
            resolve_local_media_path("/etc/passwd", provider="aws_rekognition")
        assert exc_info.value.provider == "aws_rekognition"
        assert exc_info.value.requested_path == "/etc/passwd"

    def test_unsafe_media_path_error_is_a_cloud_ai_error(self, media_root):
        with pytest.raises(CloudAIError):
            resolve_local_media_path("/etc/passwd")


class TestResolveLocalMediaPathAccepts:
    def test_file_in_root_is_accepted(self, media_root):
        resolved = resolve_local_media_path(str(media_root / "photo.jpg"))
        assert resolved == (media_root / "photo.jpg").resolve()

    def test_nested_file_in_root_is_accepted(self, media_root):
        nested = media_root / "album" / "inner.jpg"
        nested.parent.mkdir()
        nested.write_bytes(b"ok")
        assert resolve_local_media_path(str(nested)) == nested.resolve()

    def test_normalised_traversal_that_stays_inside_is_accepted(self, media_root):
        """``root/album/../photo.jpg`` resolves back into the root -- allowed."""
        (media_root / "album").mkdir()
        candidate = media_root / "album" / ".." / "photo.jpg"
        assert (
            resolve_local_media_path(str(candidate))
            == (media_root / "photo.jpg").resolve()
        )

    def test_symlink_inside_root_is_accepted(self, media_root):
        link = media_root / "alias.jpg"
        link.symlink_to(media_root / "photo.jpg")
        assert (
            resolve_local_media_path(str(link)) == (media_root / "photo.jpg").resolve()
        )

    def test_missing_file_inside_root_is_accepted_and_fails_at_open(self, media_root):
        """Containment is the guard's job; existence is the caller's problem."""
        missing = media_root / "absent.jpg"
        assert resolve_local_media_path(str(missing)) == missing.resolve()
        with pytest.raises(FileNotFoundError):
            missing.read_bytes()

    def test_returned_path_is_the_resolved_one(self, media_root):
        """Providers read the returned path, not the raw caller string."""
        (media_root / "album").mkdir()
        resolved = resolve_local_media_path(
            str(media_root / "album" / ".." / "photo.jpg")
        )
        assert ".." not in str(resolved)
        assert resolved.is_absolute()


# ===========================================================================
# Provider integration -- the guard must apply to all three providers
# ===========================================================================


class TestAWSRekognitionMediaPathGuard:
    async def test_traversal_rejected(self, media_root, secret_file):
        provider = AWSRekognition(AWS_CONFIG)
        with pytest.raises(UnsafeMediaPathError):
            await provider._prepare_image_input(str(secret_file))

    async def test_local_reads_disabled_by_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"data")
        provider = AWSRekognition(AWS_CONFIG)
        with pytest.raises(UnsafeMediaPathError):
            await provider._prepare_image_input(str(img))

    async def test_symlink_escape_rejected(self, media_root, secret_file):
        link = media_root / "innocent.jpg"
        link.symlink_to(secret_file)
        provider = AWSRekognition(AWS_CONFIG)
        with pytest.raises(UnsafeMediaPathError):
            await provider._prepare_image_input(str(link))

    async def test_permitted_file_still_reads(self, media_root):
        provider = AWSRekognition(AWS_CONFIG)
        result = await provider._prepare_image_input(str(media_root / "photo.jpg"))
        assert result == {"Bytes": b"\xff\xd8\xff\xe0"}

    async def test_s3_source_unaffected_by_guard(self, monkeypatch):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        provider = AWSRekognition(AWS_CONFIG)
        result = await provider._prepare_image_input("s3://bucket/key.jpg")
        assert result["S3Object"]["Bucket"] == "bucket"

    async def test_analyze_image_propagates_typed_error(self, media_root, secret_file):
        """The broad ``except Exception`` must not flatten the typed error."""
        provider = AWSRekognition(AWS_CONFIG)
        provider._rekognition_client = MagicMock()
        with pytest.raises(UnsafeMediaPathError):
            await provider.analyze_image(
                str(secret_file), [AnalysisType.LABEL_DETECTION]
            )


class TestAzureVisionMediaPathGuard:
    async def test_traversal_rejected(self, media_root, secret_file):
        provider = AzureVision(AZURE_CONFIG)
        with pytest.raises(UnsafeMediaPathError):
            await provider._prepare_image_input(str(secret_file))

    async def test_local_reads_disabled_by_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"data")
        provider = AzureVision(AZURE_CONFIG)
        with pytest.raises(UnsafeMediaPathError):
            await provider._prepare_image_input(str(img))

    async def test_symlink_escape_rejected(self, media_root, secret_file):
        link = media_root / "innocent.jpg"
        link.symlink_to(secret_file)
        provider = AzureVision(AZURE_CONFIG)
        with pytest.raises(UnsafeMediaPathError):
            await provider._prepare_image_input(str(link))

    async def test_permitted_file_still_reads(self, media_root):
        provider = AzureVision(AZURE_CONFIG)
        assert (
            await provider._prepare_image_input(str(media_root / "photo.jpg"))
            == b"\xff\xd8\xff\xe0"
        )

    async def test_https_source_unaffected_by_guard(self, monkeypatch):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        provider = AzureVision(AZURE_CONFIG)
        assert (
            await provider._prepare_image_input("https://example.com/img.jpg") is None
        )

    async def test_analyze_image_propagates_typed_error(self, media_root, secret_file):
        provider = AzureVision(AZURE_CONFIG)
        provider._vision_client = MagicMock()
        with pytest.raises(UnsafeMediaPathError):
            await provider.analyze_image(str(secret_file), [AnalysisType.OCR])


class TestGoogleCloudMediaPathGuard:
    """The Google provider imports ``google.cloud.vision`` inside ``analyze_image``,
    so the module is stubbed the same way the provider's own test suite does it."""

    def _provider(self):
        provider = GoogleCloudAI(GOOGLE_CONFIG)
        provider._vision_client = MagicMock()
        return provider

    @staticmethod
    def _vision_modules():
        mock_image = MagicMock()
        mock_image.return_value = MagicMock(source=MagicMock())
        mock_vision = MagicMock()
        mock_vision.Image = mock_image
        return {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }

    async def test_traversal_rejected(self, media_root, secret_file):
        provider = self._provider()
        with patch.dict("sys.modules", self._vision_modules()):
            with pytest.raises(UnsafeMediaPathError):
                await provider.analyze_image(
                    str(secret_file), [AnalysisType.LABEL_DETECTION]
                )

    async def test_local_reads_disabled_by_default(self, monkeypatch, tmp_path):
        monkeypatch.delenv(MEDIA_ROOT_ENV_VAR, raising=False)
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"data")
        provider = self._provider()
        with patch.dict("sys.modules", self._vision_modules()):
            with pytest.raises(UnsafeMediaPathError):
                await provider.analyze_image(str(img), [AnalysisType.LABEL_DETECTION])

    async def test_symlink_escape_rejected(self, media_root, secret_file):
        link = media_root / "innocent.jpg"
        link.symlink_to(secret_file)
        provider = self._provider()
        with patch.dict("sys.modules", self._vision_modules()):
            with pytest.raises(UnsafeMediaPathError):
                await provider.analyze_image(str(link), [AnalysisType.LABEL_DETECTION])

    async def test_permitted_file_still_reads(self, media_root):
        """A file inside the root reaches ``vision.Image.content`` with its bytes.

        AWS and Azure have equivalent ``test_permitted_file_still_reads`` cases;
        this closes the same coverage for Google, whose success branch assigns
        the resolved bytes to ``image.content`` rather than returning them.
        """
        provider = GoogleCloudAI(GOOGLE_CONFIG)
        provider._vision_client = AsyncMock()
        provider._vision_client.annotate_image = AsyncMock(return_value=MagicMock())

        image_instance = MagicMock(source=MagicMock())
        mock_vision = MagicMock()
        mock_vision.Image = MagicMock(return_value=image_instance)
        modules = {
            "google": _types.ModuleType("google"),
            "google.cloud": _types.ModuleType("google.cloud"),
            "google.cloud.vision": mock_vision,
        }

        with patch.dict("sys.modules", modules):
            await provider.analyze_image(
                str(media_root / "photo.jpg"), [AnalysisType.LABEL_DETECTION]
            )

        # The guard resolved the in-root file and its bytes were handed to the
        # Vision request, not the raw caller string.
        assert image_instance.content == b"\xff\xd8\xff\xe0"
        provider._vision_client.annotate_image.assert_awaited_once()
