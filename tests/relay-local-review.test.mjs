import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { execFileSync } from 'node:child_process';
import { createLocalReviewBridge } from '../apps/web/src/lib/relay-local-review.mjs';

const pythonExecutable = execFileSync('python3', ['-c', 'import sys; print(sys.executable)'], {encoding:'utf8'}).trim();

test('existing AgentAction review shape persists through actual Node -> Python -> SQLite bridge', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'relay-bridge-test-'));
  try {
    const bridge = createLocalReviewBridge({ stateDirectory: join(dir, 'state'), scriptsDirectory: resolve('scripts'), pythonExecutable });
    const actions = [{tool:'create_workflow_task',input:{title:'Inspect target',description:'Review before changes',category:'research',priority:'high'},status:'pending'}];
    const result = await bridge.persistReview(actions, 'node-bridge-v1');
    assert.equal(result.localReceipt.complete, true);
    assert.equal(result.originalActionsExecuted, false);
    assert.equal(result.originalTaskComplete, false);
    assert.equal(result.localReceipt.attempts, 1);
    const again = await bridge.persistReview(actions, 'node-bridge-v1');
    assert.equal(again.taskId, result.taskId);
    assert.deepEqual(again.localReceipt, result.localReceipt);
    const path = join(dir, 'state', result.localReceipt.evidence.artifact);
    const body = JSON.parse(await readFile(path, 'utf8'));
    assert.deepEqual(body.actions, actions);
    assert.equal(body.original_actions_executed, false);
    await writeFile(path, 'changed');
    assert.equal((await bridge.receipt(result.taskId)).complete, false);
    assert.equal((await bridge.receipt(result.taskId)).state, 'invalidated');
  } finally { await rm(dir, {recursive:true,force:true}); }
});

test('bridge rejects fulfilled or unknown actions rather than dispatching them', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'relay-bridge-test-'));
  try {
    const bridge = createLocalReviewBridge({stateDirectory:join(dir,'state'),scriptsDirectory:resolve('scripts'),pythonExecutable});
    await assert.rejects(bridge.persistReview([{tool:'dispatch_agent',input:{},status:'fulfilled'}], 'bad-status'));
    await assert.rejects(bridge.persistReview([{tool:'shell',input:{command:'whoami'},status:'pending'}], 'bad-tool'));
    await assert.rejects(bridge.receipt('../../outside'));
    assert.throws(() => createLocalReviewBridge({stateDirectory:'relative', scriptsDirectory:resolve('scripts'),pythonExecutable}));
  } finally { await rm(dir, {recursive:true,force:true}); }
});
