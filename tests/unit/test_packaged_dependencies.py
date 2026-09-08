from __future__ import annotations

from pathlib import Path


def test_archived_package_metadata_does_not_reference_python_jose() -> None:
    root = Path(__file__).resolve().parents[2]
    requires = (root / "scripts" / "archive" / "package-info" / "requires.txt").read_text()
    pkg_info = (root / "scripts" / "archive" / "package-info" / "PKG-INFO").read_text()

    assert "python-jose" not in requires.lower()
    assert "python-jose" not in pkg_info.lower()
