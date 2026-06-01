#!/usr/bin/env python3
"""
Export OpenAPI Specification
============================

Exports the EventRelay FastAPI application's OpenAPI schema to a JSON file.
This spec is used as input for Stainless SDK generation.

Usage:
    python scripts/export_openapi.py
    python scripts/export_openapi.py --output openapi/eventrelay.openapi.json
    python scripts/export_openapi.py --format yaml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure src/ is on the path so package imports resolve
_repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_repo_root / "src"))

# Set minimal env defaults required for import
os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp_export.db")


def _get_openapi_schema() -> dict:
    """Import the FastAPI app and return its OpenAPI schema dict."""
    try:
        from youtube_extension.backend.main import app  # type: ignore[import]
    except Exception as exc:
        print(f"ERROR: Failed to import FastAPI app: {exc}", file=sys.stderr)
        sys.exit(1)

    return app.openapi()


def export_json(schema: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(schema, fh, indent=2, default=str)
    print(f"OpenAPI JSON written to {output_path}")


def export_yaml(schema: dict, output_path: Path) -> None:
    try:
        import yaml  # type: ignore[import]
    except ImportError:
        print("ERROR: PyYAML is required for YAML export.  Run: pip install PyYAML", file=sys.stderr)
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        yaml.dump(schema, fh, allow_unicode=True, sort_keys=False)
    print(f"OpenAPI YAML written to {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export EventRelay OpenAPI spec")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("openapi/eventrelay.openapi.json"),
        help="Destination file path (default: openapi/eventrelay.openapi.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()

    schema = _get_openapi_schema()

    if args.format == "yaml":
        yaml_path = args.output.with_suffix(".yaml") if args.output.suffix == ".json" else args.output
        export_yaml(schema, yaml_path)
    else:
        export_json(schema, args.output)


if __name__ == "__main__":
    main()
