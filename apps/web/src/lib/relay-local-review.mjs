/**
 * Additive local-host bridge for EventRelay's existing review-only AgentAction[].
 * This is NOT production route wiring, an approval service, or an action executor.
 * @typedef {import('./action-lifecycle.ts').AgentAction} AgentAction
 */
import { execFile } from 'node:child_process';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, isAbsolute } from 'node:path';
import { promisify } from 'node:util';

const executeFile = promisify(execFile);

/**
 * Configuration is owned by a trusted local host, NEVER model/request input.
 * The host must preserve the private state directory between calls.
 * @param {{stateDirectory:string, scriptsDirectory:string, pythonExecutable:string}} config
 */
export function createLocalReviewBridge(config) {
  const { stateDirectory, scriptsDirectory, pythonExecutable } = config;
  for (const value of [stateDirectory, scriptsDirectory, pythonExecutable]) {
    if (typeof value !== 'string' || !isAbsolute(value)) {
      throw new Error('Trusted host paths must be absolute');
    }
  }

  async function invoke(args) {
    let stdout;
    try {
      ({ stdout } = await executeFile(pythonExecutable,
        ['-m', 'relay_harness', '--state', stateDirectory, ...args], {
          shell: false,
          env: { PYTHONPATH: scriptsDirectory, PYTHONUTF8: '1' },
          timeout: 10_000,
          maxBuffer: 2 * 1024 * 1024,
        }));
    } catch (error) {
      // Exit 2 is an honest, structured non-completion receipt. Timeout/unknown
      // process outcomes are NEVER retried here; caller must inspect receipt.
      if (error.code === 2 && error.stdout) stdout = error.stdout;
      else throw error;
    }
    return JSON.parse(stdout);
  }

  function checkedReceipt(receipt) {
    if (receipt.version !== 'relay.local-receipt.v1' ||
        receipt.scope !== 'local_artifact_only' ||
        receipt.external_task_complete !== false ||
        typeof receipt.complete !== 'boolean') {
      throw new Error('Invalid local-only receipt envelope');
    }
    return receipt;
  }

  return Object.freeze({
    /**
     * The actions should come from runActionAgent({..., executeTools:false}).
     * @param {AgentAction[]} actions
     * @param {string} idempotencyKey
     */
    async persistReview(actions, idempotencyKey) {
      if (typeof idempotencyKey !== 'string' || !idempotencyKey.trim() || idempotencyKey.length > 200) {
        throw new Error('Invalid idempotency key');
      }
      const json = JSON.stringify(actions);
      if (typeof json !== 'string' || Buffer.byteLength(json) > 1024 * 1024) {
        throw new Error('Review actions exceed input budget');
      }
      const directory = await mkdtemp(join(tmpdir(), 'relay-local-review-'));
      try {
        const input = join(directory, 'actions.json');
        await writeFile(input, json, { mode: 0o600, flag: 'wx' });
        const submitted = await invoke(['import-review', input, '--key', idempotencyKey]);
        if (!/^[0-9a-f]{32}$/.test(submitted.task_id)) throw new Error('Invalid journal task id');
        const localReceipt = checkedReceipt(await invoke(['run', submitted.task_id]));
        return {
          taskId: submitted.task_id,
          localReceipt,
          originalActionsExecuted: false,
          originalTaskComplete: false,
        };
      } finally {
        await rm(directory, { recursive: true, force: true });
      }
    },

    async receipt(taskId) {
      if (typeof taskId !== 'string' || !/^[0-9a-f]{32}$/.test(taskId)) {
        throw new Error('Invalid journal task id');
      }
      return checkedReceipt(await invoke(['receipt', taskId]));
    },
  });
}
