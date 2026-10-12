import { test, after } from 'node:test';
import assert from 'node:assert/strict';
// Use a dedicated test PostgreSQL instance; no production fallback.
const configured = Boolean(process.env.TEST_POSTGRES_URL);
let lock;
let close;
if (configured) {
  process.env.POSTGRES_URL = process.env.TEST_POSTGRES_URL;
  ({ withVideoGuideGenerationLock: lock, closeDatabaseConnections: close } = await import('../lib/db/queries.ts'));
}
after(async () => { if (close) await close(); });
test('PostgreSQL prevents concurrent guide generation and releases locks after failures', { skip: !configured && 'TEST_POSTGRES_URL is not configured' }, async () => {
  let release;
  let entered;
  const started = new Promise(resolve => { entered = resolve; });
  const hold = new Promise(resolve => { release = resolve; });
  const first = lock('test-user', 'test-guide', async () => { entered(); await hold; return 'saved'; });
  await started;
  try {
    const concurrent = await lock('test-user', 'test-guide', async () => { throw new Error('duplicate generation'); });
    assert.deepEqual(concurrent, { acquired: false, reason: "guide_busy" });
    assert.deepEqual(await lock('test-user', 'different-guide', async () => 'wrong'), { acquired: false, reason: 'user_busy' });
    assert.deepEqual(await lock('other-user', 'other-guide', async () => 'independent'), { acquired: true, result: 'independent' });
  } finally { release(); }
  assert.deepEqual(await first, { acquired: true, result: 'saved' });
  await assert.rejects(lock('test-user', 'test-guide', async () => { throw new Error('provider failure'); }), /provider failure/);
  assert.deepEqual(await lock('test-user', 'test-guide', async () => 'retry'), { acquired: true, result: 'retry' });
});
