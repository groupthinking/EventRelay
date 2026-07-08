"""Regression guard: the repo-root ``shared/`` package must not shadow ``src/shared``.

Running the backend or pytest from the repository root puts the root
``shared/`` package ahead of ``src/shared`` on the import path, which
historically broke ``from shared.youtube import ...`` (dropping the API v1
router in local dev and failing full-suite pytest collection).

The root ``shared/__init__.py`` now extends its ``__path__`` to include
``src/shared`` so both package roots resolve. These tests make that failure
mode impossible to reintroduce silently.
"""

import importlib.machinery
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_root_shared_path_includes_src_shared():
    """The root shared package must expose src/shared subpackages."""
    import shared

    src_shared = str(REPO_ROOT / "src" / "shared")
    root_shared = REPO_ROOT / "shared"
    if str(Path(shared.__file__).parent) == str(root_shared):
        assert src_shared in list(shared.__path__), (
            "Root shared/ package shadows src/shared without extending __path__; "
            "'from shared.youtube import ...' would break when running from the repo root."
        )


def test_shared_youtube_is_importable():
    """shared.youtube must resolve to the real implementation in src/shared."""
    import shared

    # Use PathFinder directly so fakes injected into sys.modules by other
    # tests cannot mask a genuinely broken import path.
    spec = importlib.machinery.PathFinder.find_spec(
        "youtube", path=list(shared.__path__)
    )
    assert spec is not None, "shared.youtube could not be resolved"
    assert spec.origin is not None
    assert Path(spec.origin).is_relative_to(REPO_ROOT / "src" / "shared" / "youtube")
