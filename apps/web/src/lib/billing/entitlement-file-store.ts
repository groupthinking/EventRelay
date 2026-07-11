import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import type { EntitlementRecord } from './entitlement-store';

type EntitlementFile = Record<string, EntitlementRecord>;

let cache: EntitlementFile | null = null;
let cachePath: string | null = null;

export function resolveEntitlementStorePath(): string {
  const configured = process.env.ENTITLEMENT_STORE_PATH?.trim();
  if (configured) return configured;
  return path.join(process.cwd(), '.data', 'entitlements.json');
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
  const data = await ensureLoaded(filePath);
  return data[email.trim().toLowerCase()] ?? null;
}

export async function writeEntitlementToFile(
  record: EntitlementRecord,
): Promise<void> {
  const filePath = resolveEntitlementStorePath();
  await mkdir(path.dirname(filePath), { recursive: true });
  const data = await ensureLoaded(filePath);
  data[record.email] = record;
  await writeFile(filePath, JSON.stringify(data, null, 2), 'utf8');
}

export function resetEntitlementFileStoreForTests(): void {
  cache = null;
  cachePath = null;
}