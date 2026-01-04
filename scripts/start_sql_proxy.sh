#!/bin/bash
# Start Cloud SQL Auth Proxy for uvai-vector-db (v2 syntax)
# Running on port 5433 to avoid conflicts with 5432
./cloud_sql_proxy uvai-730bb:us-central1:uvai-vector-db --port 5433
