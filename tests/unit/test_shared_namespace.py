"""Regression guard: the repo-root ``shared/`` package must not shadow ``src/shared``.

Running the backend or pytest from the repository root puts the root
``shared/`` package ahead of ``src/shared`` on the import path, which
historically broke ``from shared.youtube import ...`` (dropping the API v1
router in local dev and failing full-suite pytest collection).

The root ``shared/__init__.py`` now extends its ``__path__`` to include
``src/shared`` so both package roots resolve. These tests make that failure
mode impossible to reintroduce silently.
"""

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
