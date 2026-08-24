/**
 * Neon Postgres connection for the delivery-run store.
 *
 * Follows the same discipline as `@/lib/backend/capability`: the connection
 * string is resolved from an ordered list of accepted environment variable
 * names rather than a single hardcoded one. This project has *both*
 * `NEON_DATABASE_URL` and `POSTGRES_URL` populated, and reading only one of
 * them is precisely the class of bug that left the build backend unreachable in
 * production (audit finding F1). Resolution is centralised here so no call site
 * reads `process.env` directly.
 */

import { neon } from '@neondatabase/serverless';
import { drizzle } from 'drizzle-orm/neon-http';
import * as schema from './schema';

/**
 * Accepted connection-string variables, highest precedence first.
 *
 * Pooled URLs come first: this app runs on serverless functions where each
 * invocation opens its own connection, so the pooler is what keeps Postgres
 * from exhausting `max_connections` under concurrency. The unpooled variants
 * are last-resort fallbacks and are only correct for one-shot scripts and
 * migrations.
 */
const CONNECTION_CANDIDATES = [
  'NEON_DATABASE_URL',
  'POSTGRES_URL',
  'DATABASE_URL',
  'NEON_POSTGRES_URL',
  // Unpooled: acceptable for migrations, risky for request paths.
  'NEON_DATABASE_URL_UNPOOLED',
  'POSTGRES_URL_NON_POOLING',
] as const;

export interface DatabaseCapability {
  /** True when a usable Postgres connection string was found. */
  configured: boolean;
  /** Which env var supplied it, for diagnostics. Never the value itself. */
  source: (typeof CONNECTION_CANDIDATES)[number] | null;
  /** Host only — safe to log. Never includes credentials. */
  host: string | null;
  /** Why resolution failed, when it did. */
  reason?: string;
}

/**
 * Resolve the Postgres connection string.
 *
 * Returns the raw string separately from the diagnostic capability so callers
 * can log the capability freely without ever risking credential exposure — the
 * connection string embeds a password.
 */
function resolveConnection(
  env: Readonly<Record<string, string | undefined>> = process.env,
): { url: string | null; capability: DatabaseCapability } {
  for (const name of CONNECTION_CANDIDATES) {
    const raw = (env[name] ?? '').trim();
    if (!raw) continue;

    let host: string | null = null;
    try {
      host = new URL(raw).host;
    } catch {
      // A malformed value is worse than a missing one: it looks configured but
      // fails at query time. Skip it and keep looking for a valid candidate.
      continue;
    }

    return {
      url: raw,
      capability: { configured: true, source: name, host },
    };
  }

  return {
    url: null,
    capability: {
      configured: false,
      source: null,
      host: null,
      reason: `No Postgres connection string found. Set one of: ${CONNECTION_CANDIDATES.join(', ')}.`,
    },
  };
}

/** Diagnostics only — safe to log and to return from a health endpoint. */
export function resolveDatabaseCapability(
  env: Readonly<Record<string, string | undefined>> = process.env,
): DatabaseCapability {
  return resolveConnection(env).capability;
}

export type DeliveryDatabase = ReturnType<typeof drizzle<typeof schema>>;

let cached: DeliveryDatabase | null = null;

/**
 * Get the Drizzle client, or `null` when no database is configured.
 *
 * Returning null rather than throwing lets read paths degrade to an explicit
 * "storage unavailable" response. Write paths must use `requireDb()` instead —
 * a silently dropped write is the failure mode this whole phase exists to
 * eliminate.
 */
export function getDb(): DeliveryDatabase | null {
  if (cached) return cached;
  const { url } = resolveConnection();
  if (!url) return null;
  // Cached across invocations: neon-http is stateless over HTTP, so the client
  // is safe to reuse and rebuilding it per request wastes work.
  cached = drizzle(neon(url), { schema });
  return cached;
}

/**
 * Get the Drizzle client or throw.
 *
 * Use for every write. The error names the variables that would fix it, so an
 * operator is never sent looking for the wrong one.
 */
export function requireDb(): DeliveryDatabase {
  const db = getDb();
  if (!db) {
    throw new Error(resolveDatabaseCapability().reason ?? 'Database is not configured.');
  }
  return db;
}

/** Reset the cached client. Test-only. */
export function resetDbCache(): void {
  cached = null;
}

/**
 * Run a raw SQL statement and return the result rows as an array.
 *
 * Drizzle's `db.execute()` on the neon-http driver resolves to a
 * pg-style result *object* (`{ rows, rowCount, fields, ... }`), not an array.
 * That is easy to get wrong in a way TypeScript does not catch at the call
 * site: `const [first] = await db.execute(...)` type-checks but yields
 * `undefined` at runtime, and `result.length` is `undefined` rather than `0`,
 * so an emptiness check silently reports "not empty".
 *
 * Every raw query goes through this helper so that trap exists in exactly one
 * place instead of at every call site.
 */
export async function queryRows<T = Record<string, unknown>>(
  db: DeliveryDatabase,
  statement: Parameters<DeliveryDatabase['execute']>[0],
): Promise<T[]> {
  const result = (await db.execute(statement)) as unknown;

  // Defensive on both shapes: some drivers (and future versions) do return a
  // bare array, and this helper should keep working if that changes.
  if (Array.isArray(result)) return result as T[];
  const rows = (result as { rows?: unknown })?.rows;
  return Array.isArray(rows) ? (rows as T[]) : [];
}
