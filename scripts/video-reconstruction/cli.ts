import { randomUUID } from 'node:crypto';
import { accessSync, constants, lstatSync, mkdirSync, renameSync, statSync } from 'node:fs';
import { dirname, isAbsolute, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';
import {
  BrowserVerificationError, currentVerifierRevision, verifyInBrowser, type BrowserRun,
} from './browser.ts';
import { verifyCaptures } from './captures.ts';
import {
  exportManifestJsonSchema, finalizeManifest, loadSource, serializeManifest, sha256, verifyFiles,
} from './contract.ts';
import { emitReconstruction } from './emitter.ts';
import { jsonText, parseJsonBytes, readJson, readLocalFile, requireDirectory, writeNew } from './local-files.ts';
import { persistManifest, verifyRelayReceipt, type RelayOptions } from './relay.ts';

const defaultSource = fileURLToPath(new URL('../../apps/web/src/lib/sample-pack/auJzb1D-fag.pack.json', import.meta.url));
const defaultProfile = fileURLToPath(new URL('./profiles/auJzb1D-fag.json', import.meta.url));
const runSchema = z.strictObject({
  runId: z.string().uuid(),
  verifierRevision: z.string().regex(/^[a-f0-9]{64}$/),
});
const help = `Usage
  node --import tsx scripts/video-reconstruction/cli.ts run --out /absolute/new-dir [--source PACK] [--profile PROFILE]
  node --import tsx scripts/video-reconstruction/cli.ts verify --out /absolute/run-dir [--source PACK] [--profile PROFILE]
  node --import tsx scripts/video-reconstruction/cli.ts schema

run emits a standalone browser app, runs local Chromium checks and saves the verified evidence in EventRelay.
verify checks the current inputs, generated files, browser evidence and EventRelay artifact.
schema prints the manifest JSON Schema. Runtime verification is required for evidence bindings.

The default source and profile use the retained auJzb1D-fag sample. RECONSTRUCTION_CHROMIUM can select an
installed browser with an absolute executable path. The runner otherwise uses local or bundled Chromium.
RECONSTRUCTION_PYTHON can select an absolute Python 3 executable. The default is /usr/bin/python3.
`;

type Arguments = { command: 'run' | 'verify'; output: string; source: string; profile: string };

function parseArguments(args: string[]): Arguments {
  const [command, ...rest] = args;
  if (command !== 'run' && command !== 'verify') throw new Error('Expected run, verify or schema. Use --help for usage.');
  const options = new Map<string, string>();
  for (let i = 0; i < rest.length; i += 2) {
    const option = rest[i];
    const value = rest[i + 1];
    if (!['--out', '--source', '--profile'].includes(option) || options.has(option) || !value || value.startsWith('--')) {
      throw new Error(`Invalid or duplicate argument: ${option}`);
    }
    options.set(option, value);
  }
  const output = options.get('--out');
  if (!output || !isAbsolute(output) || resolve(output) !== output || dirname(output) === output) {
    throw new Error('--out requires a normalized absolute path beneath an existing directory');
  }
  return {
    command, output,
    source: resolve(options.get('--source') ?? defaultSource),
    profile: resolve(options.get('--profile') ?? defaultProfile),
  };
}

async function reconstruct(args: Arguments) {
  const source = await loadSource(readLocalFile(args.source, 4 * 1024 * 1024));
  const profileBytes = readLocalFile(args.profile, 128 * 1024);
  const profile = parseJsonBytes(profileBytes);
  const { files, manifest } = emitReconstruction(source, profile);
  return { files, manifest, profileFileSha256: sha256(profileBytes) };
}

type Reconstruction = Awaited<ReturnType<typeof reconstruct>>;

function configuredPython(): string | undefined {
  const python = process.env.RECONSTRUCTION_PYTHON;
  if (python === undefined) return undefined;
  if (!isAbsolute(python)) throw new Error('RECONSTRUCTION_PYTHON requires an absolute executable path');
  try {
    if (!statSync(python).isFile()) throw new Error('The configured interpreter is not a file');
    accessSync(python, constants.X_OK);
  } catch (cause) {
    throw new Error('RECONSTRUCTION_PYTHON must point to an executable file', { cause });
  }
  return python;
}

function replay(output: string, reconstruction: Reconstruction, relayOptions: RelayOptions,
  metadataDirectory = join(output, 'evidence', 'verified')) {
  requireDirectory(output);
  const app = join(output, 'app');
  const evidence = join(output, 'evidence');
  requireDirectory(evidence);
  if (lstatSync(join(evidence, 'failure.json'), { throwIfNoEntry: false })) {
    throw new Error('This run is unverified. See evidence/failure.json.');
  }
  const { manifest, profileFileSha256 } = reconstruction;
  verifyFiles(app, manifest);
  if (!readLocalFile(join(evidence, 'manifest.pending.json'), 1_048_576).equals(Buffer.from(serializeManifest(manifest)))) {
    throw new Error('Stored pending manifest differs from current source, profile or generated files');
  }
  const run = runSchema.parse(readJson(join(evidence, 'browser-run.json')));
  if (run.verifierRevision !== currentVerifierRevision()) throw new Error('Browser verifier revision mismatch');
  const rawReceipt = readLocalFile(join(metadataDirectory, 'browser-receipt.json'), 64 * 1024);
  const finalized = finalizeManifest(manifest, parseJsonBytes(rawReceipt), run);
  assertVerified(finalized, rawReceipt);
  const responsive = finalized.verifiedFunctionality.receipt.checks.find(({ id }) => id === 'responsive-light-dark');
  const inventory = readJson(join(metadataDirectory, 'captures.json'));
  verifyCaptures(evidence, inventory, finalized, responsive?.details, profileFileSha256);
  const manifestText = serializeManifest(finalized);
  if (!readLocalFile(join(metadataDirectory, 'manifest.json'), 1_048_576).equals(Buffer.from(manifestText))) {
    throw new Error('Stored final manifest differs from reconstructed and verified evidence');
  }
  const savedRelayReceipt = readLocalFile(join(metadataDirectory, 'relay-receipt.json'), 1_048_576);
  const { receipt, rawReceipt: currentRawRelayReceipt } = verifyRelayReceipt(finalized, relayOptions);
  if (!savedRelayReceipt.equals(Buffer.from(currentRawRelayReceipt))) {
    throw new Error('Stored EventRelay receipt differs from the current harness receipt');
  }
  return {
    output,
    verifiedFunctionality: finalized.verifiedFunctionality.status,
    verifiedChecks: finalized.requiredCheckIds,
    manifestSha256: sha256(manifestText),
    relay: { taskId: receipt.task_id, scope: receipt.scope, evidenceSha256: receipt.evidence.sha256 },
    fullAppOutcome: finalized.fullAppOutcome,
    heldOutcomes: finalized.heldOutcomes,
  };
}

function assertVerified(manifest: ReturnType<typeof finalizeManifest>, rawReceipt?: Buffer):
  asserts manifest is typeof manifest & { verifiedFunctionality: Extract<typeof manifest.verifiedFunctionality, { status: 'verified' }> } {
  if (manifest.verifiedFunctionality.status !== 'verified' ||
      (rawReceipt !== undefined && !rawReceipt.equals(Buffer.from(jsonText(manifest.verifiedFunctionality.receipt))))) {
    throw new Error('Browser receipt bytes do not match the canonical verified run receipt');
  }
}

async function runReconstruction(args: Arguments, reconstruction: Reconstruction, relayOptions: RelayOptions) {
  const { output } = args;
  requireDirectory(dirname(output));
  mkdirSync(output, { mode: 0o700 });
  const app = join(output, 'app');
  const evidence = join(output, 'evidence');
  const staged = join(evidence, 'partial');
  const published = join(evidence, 'verified');
  mkdirSync(app, { mode: 0o700 });
  mkdirSync(evidence, { mode: 0o700 });
  const { manifest, profileFileSha256 } = reconstruction;
  let stagedEvidence = false;
  let relayEffect: { status: 'not_attempted' | 'unconfirmed' } |
    { status: 'persisted'; taskId: string; evidenceSha256: string } = { status: 'not_attempted' };
  for (const [path, bytes] of Object.entries(reconstruction.files)) writeNew(join(app, path), bytes);
  writeNew(join(evidence, 'manifest.pending.json'), serializeManifest(manifest));
  try {
    verifyFiles(app, manifest);
    const run: BrowserRun = { runId: randomUUID(), verifierRevision: currentVerifierRevision() };
    writeNew(join(evidence, 'browser-run.json'), jsonText(run));
    const { captures, receipt } = await verifyInBrowser(app, evidence, manifest, run, profileFileSha256);
    const finalized = finalizeManifest(manifest, receipt, run);
    assertVerified(finalized);
    mkdirSync(staged, { mode: 0o700 });
    stagedEvidence = true;
    writeNew(join(staged, 'captures.json'), jsonText(captures));
    writeNew(join(staged, 'browser-receipt.json'), jsonText(finalized.verifiedFunctionality.receipt));
    writeNew(join(staged, 'manifest.json'), serializeManifest(finalized));
    relayEffect = { status: 'unconfirmed' };
    const relay = persistManifest(finalized, relayOptions);
    relayEffect = { status: 'persisted', taskId: relay.receipt.task_id, evidenceSha256: relay.receipt.evidence.sha256 };
    writeNew(join(staged, 'relay-receipt.json'), relay.rawReceipt);
    const result = replay(output, reconstruction, relayOptions, staged);
    if (lstatSync(published, { throwIfNoEntry: false })) throw new Error('Verified evidence destination already exists');
    // Publish all successful metadata together after verifying the actual local relay effect.
    renameSync(staged, published);
    return result;
  } catch (error) {
    writeNew(join(evidence, 'failure.json'), jsonText({
      status: 'unverified',
      error: error instanceof Error ? error.message : String(error),
      ...(stagedEvidence ? { partialEvidence: 'partial' } : {}),
      relayEffect,
      ...(error instanceof BrowserVerificationError ? { checks: error.checks } : {}),
    }));
    throw error;
  }
}

async function main(args: string[]) {
  if (args.length === 0 || args.includes('--help') || args.includes('-h')) {
    process.stdout.write(help);
    return;
  }
  if (args.length === 1 && args[0] === 'schema') {
    process.stdout.write(jsonText(exportManifestJsonSchema()));
    return;
  }
  const parsed = parseArguments(args);
  const relayOptions = { stateDirectory: join(parsed.output, 'relay-state'), pythonExecutable: configuredPython() };
  const reconstruction = await reconstruct(parsed);
  const result = parsed.command === 'run'
    ? await runReconstruction(parsed, reconstruction, relayOptions)
    : replay(parsed.output, reconstruction, relayOptions);
  process.stdout.write(jsonText(result));
}

main(process.argv.slice(2)).catch((error: unknown) => {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
});
