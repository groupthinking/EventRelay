#!/usr/bin/env node
/**
 * Apply the SQL files in `drizzle/` to the configured Postgres database.
 *
 * Usage:
 *   node --env-file-if-exists=../../.env.development.local scripts/apply-migrations.mjs
 *   node scripts/apply-migrations.mjs --check   # verify constraints exist, change nothing
 *
 * Why this exists rather than `drizzle-kit push`:
 *
 * The delivery schema's guarantees live in CHECK constraints and guarded
 * `DO $$ ... $$` blocks (see drizzle/0000_delivery.sql). `drizzle-kit push`
 * diffs table structure and does not reliably carry hand-written constraints,
 * so pushing would silently produce a database that accepts a `delivered` run
 * with no evidence — the exact failure the constraints prevent.
 *
 * Uses `Pool` (WebSocket) rather than `neon()` (HTTP): the HTTP driver rejects
 * multi-statement SQL with "cannot insert multiple commands into a prepared
 * statement", and these migrations are intentionally multi-statement.
 */

import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Pool } from '@neondatabase/serverless';

const HERE = dirname(fileURLToPath(import.meta.url));
const MIGRATIONS_DIR = join(HERE, '..', 'drizzle');

/**
 * Prefers an unpooled connection: DDL over the pooler can be routed across
 * different backends mid-migration.
 */
const CANDIDATES = [
  'NEON_DATABASE_URL_UNPOOLED',
  'POSTGRES_URL_NON_POOLING',
  'NEON_DATABASE_URL',
  'POSTGRES_URL',
  'DATABASE_URL',
];

/** Constraints that must exist for the delivery guarantees to hold. */
const REQUIRED_CONSTRAINTS = [
  'delivery_runs_delivered_requires_evidence',
  'delivery_runs_blocked_requires_reason',
  // Renamed from `..._is_https` by 0002: requiring https alone was too weak,
  // since `https://localhost` and `https://example.org` both satisfied it.
  'delivery_runs_deployment_url_real',
  'delivery_runs_source_shape',
  'run_gates_pass_requires_evidence',
];

function resolveConnectionString() {
  for (const name of CANDIDATES) {
    const raw = (process.env[name] ?? '').trim();
    if (raw) return { url: raw, source: name };
  }
  return { url: null, source: null };
}

async function main() {
  const checkOnly = process.argv.includes('--check');
  const { url, source } = resolveConnectionString();

  if (!url) {
    console.error(`[migrate] No connection string. Set one of: ${CANDIDATES.join(', ')}`);
    process.exit(1);
  }

  console.log(`[migrate] using ${source} -> ${new URL(url).host}`);
  const pool = new Pool({ connectionString: url });

  try {
    if (!checkOnly) {
      const files = readdirSync(MIGRATIONS_DIR)
        .filter((f) => f.endsWith('.sql'))
        .sort();

      if (files.length === 0) {
        console.error('[migrate] no .sql files found in drizzle/');
        process.exit(1);
      }

      for (const file of files) {
        // Migrations are written to be idempotent, so re-running is safe and no
        // applied-migrations ledger is needed.
        await pool.query(readFileSync(join(MIGRATIONS_DIR, file), 'utf8'));
        console.log(`[migrate] applied ${file}`);
      }
    }

    // Always verify, including after --check. Applying without verifying is how
    // a migration "succeeds" while leaving the guarantees absent.
    const { rows } = await pool.query(
      `SELECT conname FROM pg_constraint WHERE conname = ANY($1::text[])`,
      [REQUIRED_CONSTRAINTS],
    );
    const found = new Set(rows.map((r) => r.conname));
    const missing = REQUIRED_CONSTRAINTS.filter((c) => !found.has(c));

    if (missing.length > 0) {
      console.error(`[migrate] MISSING constraints: ${missing.join(', ')}`);
      console.error('[migrate] The database would accept an unproven delivery. Failing.');
      process.exit(1);
    }

    console.log(`[migrate] verified ${REQUIRED_CONSTRAINTS.length} delivery constraints present`);
  } finally {
    await pool.end();
  }
}

main().catch((error) => {
  console.error('[migrate] failed:', error.message);
  process.exit(1);
});
