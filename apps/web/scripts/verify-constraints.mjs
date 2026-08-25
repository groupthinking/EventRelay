#!/usr/bin/env node
/**
 * Prove the delivery constraints *behave*, not merely that they exist.
 *
 * `apply-migrations.mjs --check` queries `pg_constraint` for the expected
 * names. That catches a migration that never ran; it cannot catch a constraint
 * whose predicate is wrong. `delivery_runs_deployment_url_is_https` was present
 * under its expected name for weeks while happily accepting `https://localhost`
 * as a shipped deployment. This script attempts every forbidden write and fails
 * if the database accepts one.
 *
 * Usage:
 *   node --env-file-if-exists=../../.env.development.local scripts/verify-constraints.mjs
 *
 * Uses `pg` (plain libpq protocol) rather than `@neondatabase/serverless`
 * because it must run against both Neon and the throwaway Postgres container
 * CI spins up. The SQL is identical either way — the engine is what is under
 * test, not the driver.
 *
 * Safe against a shared database: the whole script runs in one transaction
 * that ends in ROLLBACK, and every assertion is a rejected write.
 */

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import pg from 'pg';

const HERE = dirname(fileURLToPath(import.meta.url));
const SQL_FILE = join(HERE, 'verify-constraints.sql');

const CANDIDATES = [
  'TEST_DATABASE_URL',
  'NEON_DATABASE_URL_UNPOOLED',
  'POSTGRES_URL_NON_POOLING',
  'NEON_DATABASE_URL',
  'POSTGRES_URL',
  'DATABASE_URL',
];

function resolveConnectionString() {
  for (const name of CANDIDATES) {
    const raw = (process.env[name] ?? '').trim();
    if (raw) return { url: raw, source: name };
  }
  return { url: null, source: null };
}

async function main() {
  const { url, source } = resolveConnectionString();
  if (!url) {
    console.error(`[constraints] No connection string. Set one of: ${CANDIDATES.join(', ')}`);
    process.exit(1);
  }

  console.log(`[constraints] using ${source} -> ${new URL(url).host}`);

  const client = new pg.Client({
    connectionString: url,
    // Neon requires TLS; the CI container does not offer it. `rejectUnauthorized`
    // stays off only for the local container case, where the endpoint is a
    // sibling process on the runner and there is no credential to protect.
    ssl: url.includes('localhost') || url.includes('127.0.0.1')
      ? false
      : { rejectUnauthorized: false },
  });

  await client.connect();

  // Surface the per-assertion RAISE NOTICE output, so a passing run reads as a
  // list of the specific things the database refused rather than a bare "ok".
  client.on('notice', (notice) => console.log(`  ${notice.message}`));

  try {
    await client.query(readFileSync(SQL_FILE, 'utf8'));
    console.log('[constraints] every forbidden write was rejected and every legitimate one accepted');
  } catch (error) {
    // A CONSTRAINT GAP message means the database accepted something it must
    // not. Anything else means the script itself could not run.
    console.error(`[constraints] FAILED: ${error.message}`);
    process.exitCode = 1;
    // The transaction is left uncommitted; ending the connection discards it.
  } finally {
    await client.end();
  }
}

main().catch((error) => {
  console.error('[constraints] failed:', error.message);
  process.exit(1);
});
