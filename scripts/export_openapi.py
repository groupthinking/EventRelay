#!/usr/bin/env python3
"""Export the FastAPI OpenAPI schema to a file for SDK generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_PATH):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from youtube_extension.backend.main import app


def export_openapi(output: Path) -> dict:
    """Generate the OpenAPI schema and write it to *output*."""
    schema = app.openapi()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as fp:
        json.dump(schema, fp, indent=2, sort_keys=True)
    return schema


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export the EventRelay FastAPI OpenAPI schema."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi/eventrelay.openapi.json"),
        help="Path to write the schema JSON (default: %(default)s)",
    )
    args = parser.parse_args()
    schema = export_openapi(args.output)
    print(f"Wrote OpenAPI schema with {len(schema.get('paths', {}))} paths to {args.output}")


if __name__ == "__main__":
    main()
