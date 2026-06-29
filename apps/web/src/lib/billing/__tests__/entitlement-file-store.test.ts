import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  writeEntitlementToFile,
  readEntitlementFromFile,
  resetEntitlementFileStoreForTests,
} from '../entitlement-file-store';

let tempDir = '';

beforeEach(async () => {
  resetEntitlementFileStoreForTests();
  tempDir = await mkdtemp(path.join(tmpdir(), 'er-entitlements-'));
  process.env.ENTITLEMENT_STORE_PATH = path.join(tempDir, 'entitlements.json');
});

afterEach(async () => {
  if (tempDir) await rm(tempDir, { recursive: true, force: true });
  delete process.env.ENTITLEMENT_STORE_PATH;
  resetEntitlementFileStoreForTests();
});

describe('entitlement file store', () => {
  it('persists across process cache resets', async () => {
    await writeEntitlementToFile({
      email: 'persist@example.com',
      plan: 'pro',
      status: 'active',
      leadModel: 'grok-4-1-fast',
      updatedAt: new Date().toISOString(),
    });
    resetEntitlementFileStoreForTests();
    const loaded = await readEntitlementFromFile('persist@example.com');
    expect(loaded?.plan).toBe('pro');
  });
});