import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import type { EntitlementRecord } from './entitlement-store';

type EntitlementFile = Record<string, EntitlementRecord>;

let cache: EntitlementFile | null = null;
let cachePath: string | null = null;

/**
 * Where the local entitlement mirror lives, or `null` when there is none.
 *
 * The `process.cwd()` default is development-only (audit finding F4). On Vercel
 * the bundle is read-only, so that path could only ever produce an EROFS throw
 * from inside the Stripe webhook's save path — the mirror never worked in
 * production, it only added a failure mode. An operator who explicitly sets
 * `ENTITLEMENT_STORE_PATH` to a writable location is honoured everywhere,
 * because that is a deliberate choice about a known-writable disk.
 */
export function resolveEntitlementStorePath(): string | null {
  const configured = process.env.ENTITLEMENT_STORE_PATH?.trim();
  if (configured) return configured;
  if (process.env.NODE_ENV !== 'production') {
    return path.join(process.cwd(), '.data', 'entitlements.json');
  }
  return null;
}

async function ensureLoaded(filePath: string): Promise<EntitlementFile> {
  if (cache && cachePath === filePath) return cache;
  try {
    const raw = await readFile(filePath, 'utf8');
    cache = JSON.parse(raw) as EntitlementFile;
  } catch {
    cache = {};
  }
  cachePath = filePath;
  return cache;
}

export async function readEntitlementFromFile(
  email: string,
): Promise<EntitlementRecord | null> {
  const filePath = resolveEntitlementStorePath();
  // No mirror configured: the durable store is the only source, which is the
  // intended production shape rather than a missing-data condition.
  if (!filePath) return null;
  const data = await ensureLoaded(filePath);
  return data[email.trim().toLowerCase()] ?? null;
}

export async function writeEntitlementToFile(
  record: EntitlementRecord,
): Promise<void> {
  const filePath = resolveEntitlementStorePath();
  if (!filePath) return;
  await mkdir(path.dirname(filePath), { recursive: true });
  const data = await ensureLoaded(filePath);
  data[record.email] = record;
  await writeFile(filePath, JSON.stringify(data, null, 2), 'utf8');
}

export function resetEntitlementFileStoreForTests(): void {
  cache = null;
  cachePath = null;
}
