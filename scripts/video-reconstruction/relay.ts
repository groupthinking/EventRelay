import { spawnSync } from 'node:child_process';
import { constants, closeSync, fstatSync, lstatSync, mkdtempSync, openSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';
import { browserBindings, canonicalJson, serializeManifest, sha256, type Manifest } from './contract.ts';

const scriptsDirectory = fileURLToPath(new URL('../', import.meta.url));
const maxBytes = 1_048_576; // relay_harness.core.MAX_BYTES
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const submitSchema = z.strictObject({ task_id: z.string(), executed: z.literal(false) });
const localReceiptSchema = z.strictObject({
  version: z.literal('relay.local-receipt.v1'),
  task_id: z.string().regex(/^[a-f0-9]{32}$/),
  state: z.literal('complete'),
  complete: z.literal(true),
  scope: z.literal('local_artifact_only'),
  external_task_complete: z.literal(false),
  reason: z.string(),
  contract_hash: hash,
  attempts: z.number().int().min(1).max(2),
  max_attempts: z.literal(2),
  evidence: z.strictObject({
    sha256: hash,
    bytes: z.number().int().positive().max(maxBytes),
    artifact: z.string(),
    all_passed: z.literal(true),
    gates: z.strictObject({
      exact_input_bytes: z.literal(true),
      sha256: z.literal(true),
      byte_budget: z.literal(true),
      required_substrings: z.literal(true),
    }),
  }),
  cost: z.strictObject({ amount: z.null(), currency: z.null(), status: z.literal('unknown'), note: z.string() }),
  history_head: hash,
  events: z.array(z.unknown()).min(1),
});

/** Both paths are trusted operator configuration. Imported data supplies neither. */
export type RelayOptions = { stateDirectory: string; pythonExecutable?: string };
export type RelayReceipt = z.infer<typeof localReceiptSchema>;

function proposalFor(manifest: Manifest) {
  const content = serializeManifest(manifest);
  const bytes = Buffer.byteLength(content);
  if (bytes > maxBytes) throw new Error('Manifest exceeds the EventRelay artifact budget');
  const hash = sha256(content);
  const idempotencyKey = `video-reconstruction:${hash}`;
  const { sourceSha256, profileSha256, generatedFilesSha256 } = browserBindings(manifest);
  const proposal = {
    version: 'relay.local-command.v1',
    idempotency_key: idempotencyKey,
    goal: 'Persist the exact local video reconstruction evidence manifest',
    context: { sourceSha256, profileSha256, generatedFilesSha256 },
    action: { tool: 'write_local_artifact', input: { content } },
    acceptance: { sha256: hash, contains: [] },
    budget: { max_attempts: 2, max_bytes: bytes },
    blockers: [], // This write only persists evidence. Full-app blockers remain inside the manifest.
  };
  return { proposal, taskId: sha256(idempotencyKey).slice(0, 32), contractHash: sha256(canonicalJson(proposal)) };
}

function callHarness(options: RelayOptions, command: 'submit' | 'run' | 'receipt', argument: string): string {
  const python = options.pythonExecutable ?? '/usr/bin/python3';
  const state = options.stateDirectory;
  if (!isAbsolute(python) || !isAbsolute(state)) throw new Error('EventRelay requires absolute operator paths');
  const result = spawnSync(python, ['-E', '-S', '-B', '-m', 'relay_harness', '--state', resolve(state), command, argument], {
    cwd: scriptsDirectory,
    env: { LANG: 'C.UTF-8', PATH: '/usr/bin:/bin' },
    encoding: 'utf8',
    timeout: 30_000,
    maxBuffer: 2 * maxBytes,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(`EventRelay ${command} failed (${result.status ?? result.signal}): ${result.stderr.trim() || result.stdout.trim()}`);
  return result.stdout;
}

function currentReceipt(options: RelayOptions, task: ReturnType<typeof proposalFor>, expectedRawReceipt?: string) {
  const rawReceipt = callHarness(options, 'receipt', task.taskId);
  const receipt = localReceiptSchema.parse(JSON.parse(rawReceipt));
  const { proposal, taskId, contractHash } = task;
  const artifact = `artifacts/${taskId}.txt`;
  if (receipt.task_id !== taskId || receipt.contract_hash !== contractHash ||
      receipt.evidence.artifact !== artifact || receipt.evidence.sha256 !== proposal.acceptance.sha256 ||
      receipt.evidence.bytes !== proposal.budget.max_bytes) {
    throw new Error('EventRelay receipt binding mismatch');
  }
  const path = join(options.stateDirectory, artifact);
  const fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
  try {
    const stat = fstatSync(fd);
    if (!stat.isFile() || stat.nlink !== 1 || stat.size !== receipt.evidence.bytes) throw new Error('Unsafe EventRelay artifact');
    const actual = readFileSync(fd);
    if (sha256(actual) !== receipt.evidence.sha256 || !actual.equals(Buffer.from(proposal.action.input.content, 'utf8'))) {
      throw new Error('EventRelay artifact content mismatch');
    }
  } finally {
    closeSync(fd);
  }
  if (expectedRawReceipt !== undefined && expectedRawReceipt !== rawReceipt) throw new Error('Stored EventRelay receipt differs from the current harness receipt');
  return { receipt, rawReceipt };
}

/** The receipt verifies the persisted local manifest. Browser proof comes from the trusted verifier. */
export function persistManifest(manifest: Manifest, options: RelayOptions) {
  const task = proposalFor(manifest);
  const temp = mkdtempSync(join(realpathSync(tmpdir()), 'uvai-video-relay-'));
  try {
    const input = join(temp, 'proposal.json');
    writeFileSync(input, JSON.stringify(task.proposal), { mode: 0o600, flag: 'wx' });
    const submitted = submitSchema.parse(JSON.parse(callHarness(options, 'submit', input)));
    if (submitted.task_id !== task.taskId) throw new Error('EventRelay submitted task ID mismatch');
    callHarness(options, 'run', task.taskId);
    return currentReceipt(options, task);
  } finally {
    rmSync(temp, { force: true, recursive: true });
  }
}

/** Re-read the live harness and compare against any supplied receipt. */
export function verifyRelayReceipt(manifest: Manifest, options: RelayOptions, expectedRawReceipt?: string) {
  const state = options.stateDirectory;
  if (!isAbsolute(state) || !lstatSync(join(state, 'journal.sqlite3')).isFile()) {
    throw new Error('A current EventRelay state journal is required');
  }
  return currentReceipt(options, proposalFor(manifest), expectedRawReceipt);
}
