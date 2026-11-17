import { test } from 'node:test';
import assert from 'node:assert/strict';
import { auditWorkflowTaskCapacity } from '../audit-workflow-task-capacity.mjs';

const owner = 'a'.repeat(64);
const id = 'b'.repeat(64);
const taskKey = `er:workflow-task:v1:${owner}:${id}`;
const quotaKey = `er:workflow-task-quota:v1:${owner}`;
const record = JSON.stringify({ id, jobId: 'preview_1', createdAt: '2026-11-05T00:00:00.000Z', title: 'Review evidence', description: 'Inspect source', category: 'research', priority: 'high' });

function store({ quota = 'v1:1', taskTtl = -1, secondScanKeys = [taskKey], recordValue = record } = {}) {
  const calls = [];
  let scanCount = 0;
  const fetchImpl = async (_url, opts) => {
    const args = JSON.parse(opts.body);
    calls.push(args);
    assert.equal(opts.method, 'POST');
    assert.equal(opts.redirect, 'error');
    assert.equal(opts.cache, 'no-store');
    assert.ok(['SCAN', 'GET', 'PTTL'].includes(args[0]), 'read-only commands only');
    let result;
    switch (args[0]) {
      case 'SCAN': result = ['0', scanCount++ === 0 ? [taskKey] : secondScanKeys]; break;
      case 'GET': result = args[1] === taskKey ? recordValue : args[1] === quotaKey ? quota : null; break;
      case 'PTTL': result = args[1] === taskKey ? taskTtl : -1; break;
      default: throw new Error('Unexpected Redis command');
    }
    return Response.json({ result });
  };
  return { fetchImpl, calls };
}
const config = { url: 'https://isolated.invalid', token: 'test-only' };

test('audits twice, reads without writing, and does not authorize a production migration', async () => {
  const mock = store();
  const result = await auditWorkflowTaskCapacity({ ...config, fetchImpl: mock.fetchImpl });
  assert.equal(result.taskCount, 1);
  assert.equal(result.inventoryStableAcrossTwoScans, true);
  assert.deepEqual(result.anomalies, []);
  assert.equal(result.productionMigrationAuthorized, false);
  assert.equal(result.owners[0].recordedReservations, 1);
  assert.deepEqual(mock.calls.map(call => call[0]), ['SCAN', 'SCAN', 'GET', 'PTTL', 'GET', 'PTTL']);
});

test('refuses unsafe URLs before sending credentials', async () => {
  const mock = store();
  await assert.rejects(auditWorkflowTaskCapacity({ ...config, url: 'http://isolated.invalid', fetchImpl: mock.fetchImpl }), /HTTPS/);
  await assert.rejects(auditWorkflowTaskCapacity({ ...config, url: 'https://user:pass@isolated.invalid', fetchImpl: mock.fetchImpl }), /HTTPS/);
  assert.equal(mock.calls.length, 0);
});

test('flags missing, undercounted, or expiring quota state', async () => {
  for (const quota of [null, 'v1:0', 'v1:2', 'v1:01']) {
    const mock = store({ quota });
    const result = await auditWorkflowTaskCapacity({ ...config, fetchImpl: mock.fetchImpl });
    assert.ok(result.anomalies.some(a => /quota/.test(a.type)));
    assert.equal(result.productionMigrationAuthorized, false);
  }
});

test('detects observable inventory drift without assuming the store is empty', async () => {
  const mock = store({ secondScanKeys: [] });
  const result = await auditWorkflowTaskCapacity({ ...config, fetchImpl: mock.fetchImpl });
  assert.equal(result.inventoryStableAcrossTwoScans, false);
  assert.deepEqual(result.anomalies, [{ type: 'inventory_changed_between_scans' }]);
});

test('flags nonpermanent or invalid task records', async () => {
  const mock = store({ taskTtl: 1000, recordValue: '{bad JSON' });
  const result = await auditWorkflowTaskCapacity({ ...config, fetchImpl: mock.fetchImpl });
  assert.ok(result.anomalies.some(a => a.type === 'task_not_permanent'));
  assert.ok(result.anomalies.some(a => a.type === 'invalid_task_record'));
});

test('fails closed on unexpected storage transport response', async () => {
  await assert.rejects(auditWorkflowTaskCapacity({ ...config, fetchImpl: async () => Response.json({ error: 'denied', result: [] }) }), /Invalid audit storage response/);
});
