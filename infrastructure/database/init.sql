-- Database initialization script
-- This file is mounted to /docker-entrypoint-initdb.d/init.sql
-- It runs when the postgres container starts with an empty data volume.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
-- Enable pgvector if available