from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "docs" / "external" / "chatgpt-exports" / "adintelligence-transfer"
SCRIPT = ARTIFACT_DIR / "rebuild_adintelligence_app.py"


def test_rebuild_adintelligence_app_verifies_sha256() -> None:
    manifest = json.loads((ARTIFACT_DIR / "manifest.json").read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp_dir:
        output = Path(tmp_dir) / "reassembled.zip"
        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--manifest",
                str(ARTIFACT_DIR / "manifest.json"),
                "--output",
                str(output),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        assert output.exists()
        assert "SHA-256:" in completed.stdout

        rebuilt_bytes = output.read_bytes()
        assert hashlib.sha256(rebuilt_bytes).hexdigest() == manifest["sha256"]

        with zipfile.ZipFile(output) as zip_file:
            names = zip_file.namelist()
            assert "adintelligence/README.md" in names
            assert "adintelligence/app.py" in names
