"""Regression guard: ``src/shared`` must be importable as ``shared`` from the repo root.

The project-root ``shared/`` package was renamed to ``project_shared/`` so it no
longer collides with ``src/shared`` on ``sys.path``. Running pytest from the
repository root must still resolve ``from shared.youtube import ...`` to
``src/shared/youtube``. These tests make that failure mode impossible to
reintroduce silently.
"""

import importlib.machinery
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


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


def test_root_project_shared_does_not_shadow_src_shared():
    """The project-root project_shared/ package must not collide with src/shared."""
    root_shared = REPO_ROOT / "shared"
    project_shared = REPO_ROOT / "project_shared"
    assert not root_shared.exists(), (
        "Repo-root shared/ still exists and would shadow src/shared/ on sys.path"
    )
    assert project_shared.exists(), (
        "project_shared/ directory missing after rename"
    )
