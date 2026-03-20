import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.export_openapi import export_openapi


def test_export_openapi_writes_schema(tmp_path: Path) -> None:
    output = tmp_path / "openapi.json"
    schema = export_openapi(output)

    assert output.exists()
    data = output.read_text(encoding="utf-8")
    assert '"paths"' in data
    assert "/api/v1/transcript-action" in data
    assert schema.get("info", {}).get("title") in {"YouTube Extension API", "UVAI API"}
