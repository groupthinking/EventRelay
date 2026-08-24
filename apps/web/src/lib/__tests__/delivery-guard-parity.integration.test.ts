/**
 * Cross-layer agreement between the reducer guard and the database constraint.
 *
 * "Delivered means shipped" is enforced twice on purpose:
 *
 *  1. `missingDeliveryEvidence()` in `@/lib/delivery-lifecycle` (application)
 *  2. the `delivery_runs_delivered_needs_evidence` and
 *     `delivery_runs_deployment_url_real` CHECK constraints (database)
 *
 * Two independent implementations of the same rule can drift. If the TypeScript
 * `PLACEHOLDER_HOSTS` list gained an entry the SQL CHECK did not (or the
 * reverse), the layered defence would quietly become single-layered, and the
 * gap would only be discovered by a fake "delivered" row reaching production.
 *
 * This suite feeds the same candidate deployments to both layers and asserts
 * they reach the same verdict, so drift fails CI instead of shipping.
 *
 * Requires a database connection; skips cleanly when one is absent so local
 * runs without credentials still pass.
 */

import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { sql } from 'drizzle-orm';
import { getDb, resolveDatabaseCapability } from '@/lib/db/client';
import { isRealDeploymentUrl } from '@/lib/delivery-lifecycle';

const TEST_USER = 'guard-parity-test-user';

/**
 * Candidate deployment URLs spanning real hosts and every placeholder shape.
 * Both layers must agree on each one.
 */
const CANDIDATES: string[] = [
  // Real, live https hosts — both layers must accept.
  'https://widget.vercel.app',
  'https://api.uvai.io',
  'https://staging.acme.dev',
  'https://widget.vercel.app/dashboard?tab=1',
  // Plain http — not "shipped"; both layers must reject.
  'http://staging.acme.dev',
  'http://localhost:3000',
  // Loopback and unspecified addresses, over either scheme.
  'https://localhost',
  'https://localhost:3000',
  'https://sub.localhost',
  'https://127.0.0.1',
  'http://127.0.0.1:8000',
  'https://0.0.0.0:5000',
  // RFC 2606 reserved documentation domains, bare and as subdomains.
  'https://example.com/app',
  'https://example.org',
  'https://example.net',
  'https://docs.example.com',
  // Malformed / wrong scheme.
  'ftp://files.acme.test',
  'not-a-url',
  '',
];

const capability = resolveDatabaseCapability();
const hasDb = capability.configured;

// A skipped parity suite proves nothing, so say so loudly rather than passing
// green and silent. This is how the first version of this file went unnoticed:
// it read a field that did not exist, so every case skipped.
if (!hasDb) {
  console.warn(
    `[v0] delivered-guard parity suite SKIPPED — no database configured. ${capability.reason ?? ''}`,
  );
}

/**
 * Ask the database whether it will store a `delivered` row with this URL.
 * Returns true when the insert succeeded (i.e. the DB considers it real).
 */
async function databaseAccepts(url: string): Promise<boolean> {
  const db = getDb();
  if (!db) throw new Error('no database');
  try {
    await db.execute(sql`
      INSERT INTO delivery_runs
        (user_id, title, status, source_kind, source_url,
         repo_url, tests_passed_at, deployment_url, delivered_at)
      VALUES
        (${TEST_USER}, ${'parity ' + url}, 'delivered', 'video', 'https://x.test/v',
         'https://github.com/o/r', now(), ${url}, now())
    `);
    return true;
  } catch {
    // A constraint violation is the database refusing the row.
    return false;
  }
}

describe.skipIf(!hasDb)('delivered-guard parity: application vs database', () => {
  beforeAll(async () => {
    const db = getDb();
    await db?.execute(sql`DELETE FROM delivery_runs WHERE user_id = ${TEST_USER}`);
  });

  afterAll(async () => {
    const db = getDb();
    await db?.execute(sql`DELETE FROM delivery_runs WHERE user_id = ${TEST_USER}`);
  });

  it.each(CANDIDATES)('both layers agree on %j', async (url) => {
    const appVerdict = isRealDeploymentUrl(url);
    const dbVerdict = await databaseAccepts(url);

    expect(
      appVerdict,
      `Layer drift for ${JSON.stringify(url)}: application says ` +
        `${appVerdict ? 'REAL' : 'placeholder'} but the database says ` +
        `${dbVerdict ? 'REAL' : 'placeholder'}. Update PLACEHOLDER_HOSTS in ` +
        `delivery-lifecycle.ts and the delivery_runs_deployment_url_real CHECK ` +
        `constraint together.`,
    ).toBe(dbVerdict);
  });

  it('rejects a delivered row missing tests, at both layers', async () => {
    const db = getDb();
    let dbRejected = false;
    try {
      await db!.execute(sql`
        INSERT INTO delivery_runs
          (user_id, title, status, source_kind, source_url, repo_url, deployment_url, delivered_at)
        VALUES
          (${TEST_USER}, 'no tests', 'delivered', 'video', 'https://x.test/v',
           'https://github.com/o/r', 'https://real.vercel.app', now())
      `);
    } catch {
      dbRejected = true;
    }
    expect(dbRejected).toBe(true);
  });
});
