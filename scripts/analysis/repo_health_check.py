#!/usr/bin/env python3
"""
Repository Health Check & Cross-Reference Script.

This script performs two main functions:
1. Runs key analytical queries against BigQuery (Repository Tree).
2. Cross-references BigQuery data with Cloud SQL (Vector DB) to identify missing embeddings.

requirements:
  pip install google-cloud-bigquery psycopg2-binary python-dotenv tableprint
"""
import os
import time
from typing import List, Set
import psycopg2
from google.cloud import bigquery
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Configuration
BQ_PROJECT_ID = "uvai-730bb"
BQ_DATASET_ID = "eventrelay_metadata"
BQ_TABLE_ID = "repository_tree"
DB_HOST = "127.0.0.1"
DB_PORT = "5433"  # Cloud SQL Proxy
DB_NAME = "uvai_vector_db"  # Updated from mcp_config.json
DB_USER = "postgres"

# Get DB credentials from env if available, else standard defaults for proxy
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_bq_client():
    return bigquery.Client(project=BQ_PROJECT_ID)


def get_pg_connection():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    # Fallback to local proxy typical settings
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=os.environ.get(
            "DB_PASSWORD", "ChangeMe123!"
        ),  # Updated default password
    )


def run_bq_query(client, query, description):
    print(f"--- {description} ---")
    query_job = client.query(query)
    results = query_job.result()
    rows = list(results)
    print(f"Result Count: {len(rows)}")
    for row in rows[:5]:  # Show first 5
        print(dict(row))
    if len(rows) > 5:
        print("...")
    return rows


def check_cross_reference():
    print("\n--- Cross-Reference: BigQuery Repo Tree vs Cloud SQL Vector DB ---")

    # 1. Get all file paths from BigQuery
    bq_client = get_bq_client()
    bq_query = f"""
        SELECT path
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}`
        WHERE NOT is_directory
    """
    print("Fetching file list from BigQuery...")
    bq_files: Set[str] = set()
    for row in bq_client.query(bq_query).result():
        # BigQuery path is full absolute path usually, or relative depending on ingestion.
        # Tree ingestion script produces full paths.
        # We need to normalize to relative paths from repo root for comparison if Vector DB stores relative.
        # Vector DB stores 'filename' in metadata which is relative path (see ingest_repo.py).

        # Heuristic to make relative: find project root in path
        path = row.path
        if "/EventRelay/" in path:
            rel_path = path.split("/EventRelay/")[-1]
            bq_files.add(rel_path)
        else:
            # Fallback or assumption
            bq_files.add(path)

    print(f"Found {len(bq_files)} files in Repository Tree (BigQuery).")

    # 2. Get all file paths from Cloud SQL
    print("Fetching file list from Cloud SQL Vector DB (metadata->>filename)...")
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        cur.execute("SELECT metadata->>'filename' as filename FROM vector_items")
        pg_files: Set[str] = set()
        for row in cur.fetchall():
            if row[0]:
                pg_files.add(row[0])
        conn.close()
        print(f"Found {len(pg_files)} files in Vector DB (Cloud SQL).")

        # 3. Analyze differences
        missing_in_vector_db = bq_files - pg_files
        missing_in_bq = pg_files - bq_files

        print(f"\nFiles in Repo but NOT in Vector DB: {len(missing_in_vector_db)}")
        # Filter out common ignored files to see meaningful gaps
        meaningful_missing = [
            f
            for f in missing_in_vector_db
            if not f.startswith(".")
            and not f.endswith(".pyc")
            and "/node_modules/" not in f
        ]
        print(f"Meaningful Missing (approx): {len(meaningful_missing)}")
        if meaningful_missing:
            print("First 10 missing:")
            for f in meaningful_missing[:10]:
                print(f" - {f}")

        print(f"\nFiles in Vector DB but NOT in Repo (Ghosts?): {len(missing_in_bq)}")
        if missing_in_bq:
            print("First 10 ghosts:")
            for f in list(missing_in_bq)[:10]:
                print(f" - {f}")

    except Exception as e:
        print(f"Error connecting to Cloud SQL: {e}")


def main():
    print("Starting Repository Health Check...")

    # Run Dashboard Queries (Sample)
    bq_client = get_bq_client()

    # 1. Tech Stack
    q1 = f"""
        SELECT extension, COUNT(*) as count
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}`
        WHERE extension IS NOT NULL
        GROUP BY extension ORDER BY count DESC LIMIT 5
    """
    run_bq_query(bq_client, q1, "Tech Stack Distribution")

    # 2. Dead Code Candidates
    q2 = f"""
        SELECT path FROM `{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{BQ_TABLE_ID}`
        WHERE regexp_contains(lower(path), r'archive|deprecated|old|legacy')
        LIMIT 5
    """
    run_bq_query(bq_client, q2, "Legacy/Archive Candidates (Sample)")

    # Cross Reference
    check_cross_reference()


if __name__ == "__main__":
    main()
