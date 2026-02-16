#!/usr/bin/env python3
"""
Parse FULL-TREE.html and send to BigQuery.

Usage:
    python scripts/tree_to_bigquery.py

Requires:
    pip install google-cloud-bigquery beautifulsoup4 lxml
"""
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from google.cloud import bigquery


# Configuration
PROJECT_ID = "uvai-730bb"
DATASET_ID = "eventrelay_metadata"
TABLE_ID = "repository_tree"
FULL_TREE_PATH = Path(__file__).parent.parent / "FULL-TREE.html"

# BigQuery Schema
SCHEMA = [
    bigquery.SchemaField("path", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("depth", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("is_directory", "BOOLEAN", mode="REQUIRED"),
    bigquery.SchemaField("extension", "STRING", mode="NULLABLE"),
]


def parse_tree_html(html_path: Path) -> list[dict[str, Any]]:
    """Parse FULL-TREE.html and extract file/directory entries."""
    print(f"Reading {html_path}...")
    with open(html_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")

    entries: list[dict[str, Any]] = []
    path_stack: list[str] = []

    # Tree prefixes to strip
    tree_chars = re.compile(r"^[│├└─ \xa0]+")  # includes nbsp

    for p_tag in soup.find_all("p", class_=["p1", "p2"]):
        text = p_tag.get_text()

        # Skip shell prompts and non-tree lines
        if "garvey@" in text or text.strip() == "" or "[error opening dir]" in text:
            continue
        if text.strip() in (".", "0 directories, 0 files"):
            continue

        # Clean the line
        clean = tree_chars.sub("", text).strip()
        if not clean:
            continue

        # Calculate depth from leading characters
        match = tree_chars.match(text)
        prefix_len = len(match.group()) if match else 0
        # Each level is roughly 4 characters of tree prefix
        depth = prefix_len // 4

        # Adjust path stack
        while len(path_stack) > depth:
            path_stack.pop()

        # Build full path
        path_stack.append(clean)
        full_path = "/".join(path_stack)

        # Determine if directory (heuristic: no extension, or contains symlink arrow)
        # Directories in `tree` output typically don't have extensions
        is_symlink = " -> " in clean
        name = clean.split(" -> ")[0] if is_symlink else clean
        is_directory = "." not in name or name.startswith(".") and name.count(".") == 1

        # Get extension
        ext = None
        if not is_directory and "." in name:
            ext = name.rsplit(".", 1)[-1]

        entries.append(
            {
                "path": full_path,
                "name": name,
                "depth": depth,
                "is_directory": is_directory,
                "extension": ext,
            }
        )

    print(f"Parsed {len(entries)} entries.")
    return entries


def load_to_bigquery(entries: list[dict[str, Any]]) -> None:
    """Load entries to BigQuery using a load job (handles large payloads)."""
    client = bigquery.Client(project=PROJECT_ID)

    # Create dataset if not exists
    dataset_ref = client.dataset(DATASET_ID)
    try:
        client.get_dataset(dataset_ref)
        print(f"Dataset {DATASET_ID} exists.")
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset)
        print(f"Created dataset {DATASET_ID}.")

    # Create or replace table
    table_ref = dataset_ref.table(TABLE_ID)
    table = bigquery.Table(table_ref, schema=SCHEMA)

    # Delete existing table if present
    try:
        client.delete_table(table_ref)
        print(f"Deleted existing table {TABLE_ID}.")
    except Exception:
        pass

    client.create_table(table)
    print(f"Created table {TABLE_ID}.")

    # Write JSON-L to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as tf:
        for entry in entries:
            tf.write(json.dumps(entry) + "\n")
        temp_path = tf.name

    print(f"Wrote {len(entries)} entries to {temp_path}")

    # Load from file
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=SCHEMA,
    )
    with open(temp_path, "rb") as source_file:
        job = client.load_table_from_file(source_file, table_ref, job_config=job_config)

    job.result()  # Wait for completion
    print(f"Loaded {job.output_rows} rows into {DATASET_ID}.{TABLE_ID}.")

    # Cleanup
    Path(temp_path).unlink()


def main() -> None:
    entries = parse_tree_html(FULL_TREE_PATH)
    if not entries:
        print("No entries found. Exiting.")
        return
    load_to_bigquery(entries)
    print("Done!")


if __name__ == "__main__":
    main()
