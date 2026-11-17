/**
 * Read-only inventory for PR #2472. Never initializes, repairs, or writes quota metadata.
 * Set dedicated WORKFLOW_TASK_AUDIT_URL and WORKFLOW_TASK_AUDIT_TOKEN explicitly.
 */
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';

const TASK_PREFIX = 'er:workflow-task:v1:';
const TASK_KEY = /^er:workflow-task:v1:([a-f0-9]{64}):([a-f0-9]{64})$/;
const COUNT = /^v1:(0|[1-9][0-9]*)$/;
const MAX_SAFE = BigInt(Number.MAX_SAFE_INTEGER);

export async function auditWorkflowTaskCapacity({ url, token, fetchImpl = fetch, maxKeys = 10_000 }) {
  if (typeof url !== 'string' || typeof token !== 'string' || !token.trim()) throw new Error('Explicit audit credentials required');
  let endpoint;
  try { endpoint = new URL(url); } catch { throw new Error('Invalid audit URL'); }
  if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password || endpoint.search || endpoint.hash) {
    throw new Error('Audit endpoint must be HTTPS without userinfo or query parameters');
  }
  if (!Number.isSafeInteger(maxKeys) || maxKeys < 1 || maxKeys > 100_000) throw new Error('Invalid audit key limit');
  const command = async (args) => {
    const response = await fetchImpl(endpoint.href, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(args), redirect: 'error', cache: 'no-store', signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) throw new Error('Audit storage request failed');
    const payload = await response.json();
    if (!payload || typeof payload !== 'object' || payload.error || !Object.hasOwn(payload, 'result')) {
      throw new Error('Invalid audit storage response');
    }
    return payload.result;
  };
  const scan = async () => {
    const keys = new Set();
    let cursor = '0';
    const visited = new Set();
    for (let pages = 0; pages < 10_000; pages++) {
      const result = await command(['SCAN', cursor, 'MATCH', `${TASK_PREFIX}*`, 'COUNT', '500']);
      if (!Array.isArray(result) || result.length !== 2 || !Array.isArray(result[1])) throw new Error('Invalid Redis SCAN response');
      const next = String(result[0]);
      if (!/^\d+$/.test(next) || visited.has(`${cursor}:${next}`)) throw new Error('Invalid or repeating Redis SCAN cursor');
      visited.add(`${cursor}:${next}`);
      for (const key of result[1]) {
        if (typeof key !== 'string' || !key.startsWith(TASK_PREFIX)) throw new Error('Invalid task inventory key');
        keys.add(key);
        if (keys.size > maxKeys) throw new Error('Task inventory exceeded the configured key limit');
      }
      if (next === '0') return keys;
      cursor = next;
    }
    throw new Error('Task inventory exceeded maximum scan pages');
  };

  // Repeat enumeration; this detects observable drift but never proves a writer freeze.
  const first = await scan();
  const second = await scan();
  const anomalies = [];
  const sameKeys = first.size === second.size && [...first].every(key => second.has(key));
  if (!sameKeys) anomalies.push({ type: 'inventory_changed_between_scans' });
  const groups = new Map();
  for (const key of [...second].sort()) {
    const match = TASK_KEY.exec(key);
    if (!match) { anomalies.push({ type: 'malformed_task_key' }); continue; }
    const [, ownerHash, id] = match;
    groups.set(ownerHash, (groups.get(ownerHash) ?? 0) + 1);
    const [record, ttl] = await Promise.all([command(['GET', key]), command(['PTTL', key])]);
    if (ttl !== -1) anomalies.push({ type: 'task_not_permanent', ownerHash, taskId: id });
    try {
      if (typeof record !== 'string') throw new Error('missing');
      const item = JSON.parse(record);
      if (!item || item.id !== id || typeof item.jobId !== 'string' || !item.jobId.trim() ||
          typeof item.createdAt !== 'string' || !Number.isFinite(Date.parse(item.createdAt)) ||
          typeof item.title !== 'string' || !item.title.trim() || item.title.length > 300 ||
          typeof item.description !== 'string' || !item.description.trim() || item.description.length > 10_000 ||
          !['setup', 'build', 'deploy', 'learn', 'research', 'configure'].includes(item.category) ||
          !['high', 'medium', 'low'].includes(item.priority)) throw new Error('malformed');
    } catch { anomalies.push({ type: 'invalid_task_record', ownerHash, taskId: id }); }
  }
  const owners = [];
  for (const [ownerHash, observedRecords] of [...groups].sort(([a], [b]) => a.localeCompare(b))) {
    const key = `er:workflow-task-quota:v1:${ownerHash}`;
    const [raw, ttl] = await Promise.all([command(['GET', key]), command(['PTTL', key])]);
    const count = typeof raw === 'string' && COUNT.test(raw) ? BigInt(raw.slice(3)) : null;
    const validCount = count !== null && count <= MAX_SAFE;
    const recordedReservations = validCount ? Number(count) : null;
    if (!validCount || ttl !== -1) anomalies.push({ type: 'invalid_or_uninitialized_quota', ownerHash });
    else if (recordedReservations !== observedRecords) {
      anomalies.push({ type: 'quota_requires_reconciliation', ownerHash, observedRecords, recordedReservations });
    }
    owners.push({ ownerHash, observedRecords, recordedReservations, quotaPermanent: ttl === -1 });
  }
  return {
    format: 'eventrelay.workflow-task-capacity-audit.v1',
    mode: 'read-only', inventoryStableAcrossTwoScans: sameKeys,
    taskCount: second.size, owners, anomalies,
    // An operator must independently demonstrate a frozen writer set and storage identity.
    productionMigrationAuthorized: false,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  if (process.argv.includes('--help')) {
    console.log('Read-only quota inventory: set WORKFLOW_TASK_AUDIT_URL and WORKFLOW_TASK_AUDIT_TOKEN; run node apps/web/scripts/audit-workflow-task-capacity.mjs');
  } else {
    try {
      const report = await auditWorkflowTaskCapacity({
        url: process.env.WORKFLOW_TASK_AUDIT_URL,
        token: process.env.WORKFLOW_TASK_AUDIT_TOKEN,
      });
      console.log(JSON.stringify(report, null, 2));
      if (report.anomalies.length) process.exitCode = 2;
    } catch {
      console.error('Read-only quota audit failed; no changes were made. Verify the endpoint, credentials, and storage responses.');
      process.exitCode = 1;
    }
  }
}
