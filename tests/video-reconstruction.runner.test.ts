import assert from 'node:assert/strict';
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, realpathSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test, { type TestContext } from 'node:test';
import { setTimeout as delay } from 'node:timers/promises';
import { fileURLToPath } from 'node:url';
import { parseManifest, loadSource, readProfile, verifyFiles, type Manifest } from '../scripts/video-reconstruction/contract.ts';
import { emitReconstruction } from '../scripts/video-reconstruction/emitter.ts';
import { verifyRelayReceipt } from '../scripts/video-reconstruction/relay.ts';

const root = fileURLToPath(new URL('../', import.meta.url));
const sourcePath = join(root, 'apps/web/src/lib/sample-pack/auJzb1D-fag.pack.json');
const profilePath = join(root, 'scripts/video-reconstruction/profiles/auJzb1D-fag.json');
const cliPath = join(root, 'scripts/video-reconstruction/cli.ts');

function temporaryDirectory(t: TestContext) {
  const temp = mkdtempSync(join(realpathSync(tmpdir()), 'uvai-reconstruction-test-'));
  t.after(() => rmSync(temp, { force: true, recursive: true }));
  return temp;
}

function invokeCli(args: string[], env = process.env) {
  const execution = spawnSync(process.execPath, ['--import', 'tsx', cliPath, ...args], {
    cwd: root, env, encoding: 'utf8', timeout: 150_000, maxBuffer: 2 * 1024 * 1024,
  });
  if (execution.error) throw execution.error;
  return execution;
}

const cli = (...args: string[]) => invokeCli(args);

function writeAttachmentProfile(directory: string) {
  const original = JSON.parse(readFileSync(profilePath, 'utf8'));
  const path = join(directory, 'attachment-profile.json');
  writeFileSync(path, JSON.stringify({
    ...original,
    description: original.description + ' Encoding fixture �.',
    mappings: [original.mappings[0]],
  }));
  return path;
}

function replaceWithMalformedByte(bytes: Buffer, text: string): Buffer {
  const marker = Buffer.from(text);
  const offset = bytes.indexOf(marker);
  assert.ok(offset >= 0);
  return Buffer.concat([bytes.subarray(0, offset), Buffer.from([0xff]), bytes.subarray(offset + marker.length)]);
}

test('emitter writes deterministic static files for a validated profile', async (t) => {
  const source = await loadSource(readFileSync(sourcePath));
  const profile = readProfile(JSON.parse(readFileSync(profilePath, 'utf8')), source);
  const first = emitReconstruction(source, profile);
  assert.deepEqual(emitReconstruction(source, profile), first);
  assert.deepEqual(first.manifest.requiredCheckIds, [
    'youtube-attachment', 'summary-renderer', 'box-renderer', 'invalid-input', 'offline-and-console', 'responsive-light-dark',
  ]);
  const output = temporaryDirectory(t);
  for (const [path, data] of Object.entries(first.files)) writeFileSync(join(output, path), data);
  verifyFiles(output, first.manifest);
  const html = readFileSync(join(output, 'index.html'), 'utf8');
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /form-action 'none'/);
  assert.match(html, /<script defer src="app.js"><\/script>/);
  assert.match(html, /https:\/\/www.youtube.com\/watch\?v=auJzb1D-fag/);
  assert.match(html, /G-REQ-01/);
  assert.match(html, /G-REQ-02/);
  assert.match(html, /G-REQ-03/);
  assert.match(html, /Run model<\/button>/);
  assert.equal(first.manifest.verifiedFunctionality.status, 'unverified');
  assert.equal(first.manifest.fullAppOutcome, 'HOLD');
});

test('emitter escapes profile copy and limits the app to mapped routes', async () => {
  const source = await loadSource(readFileSync(sourcePath));
  const original = JSON.parse(readFileSync(profilePath, 'utf8'));
  const profile = readProfile({
    ...original,
    name: '<script>untrusted title</script>',
    description: '"<input name=untrusted-description>"',
    mappings: [original.mappings[2]],
  }, source);
  const single = emitReconstruction(source, profile);
  assert.doesNotMatch(single.files['index.html'], /<script>untrusted title|<input name=untrusted-description|data-view="video"/);
  assert.match(single.files['index.html'], /&lt;script&gt;untrusted title/);
  assert.match(single.files['index.html'], /data-view="spatial"/);
  assert.deepEqual(single.manifest.requiredCheckIds, ['box-renderer', 'invalid-input', 'offline-and-console', 'responsive-light-dark']);
  assert.throws(() => emitReconstruction(source, {
    ...profile, mappings: [{ ...profile.mappings[0], capability: 'unsupported-renderer' }],
  }));
});

test('CLI exposes usage and schema and rejects invalid output paths before browser work', (t) => {
  const rootDir = temporaryDirectory(t);
  const usage = cli('--help');
  assert.equal(usage.status, 0, usage.stderr);
  assert.match(usage.stdout, /run --out.*new-dir/);
  assert.match(usage.stdout, /verify --out.*run-dir/);
  const schema = cli('schema');
  assert.equal(schema.status, 0, schema.stderr);
  assert.match(JSON.parse(schema.stdout).$schema, /2020-12/);

  const relative = cli('run', '--out', 'relative');
  assert.equal(relative.status, 1);
  assert.match(relative.stderr, /normalized absolute path/);
  const traversal = cli('run', '--out', rootDir + '/nested/../run');
  assert.equal(traversal.status, 1);
  assert.match(traversal.stderr, /normalized absolute path/);

  const existing = join(rootDir, 'existing');
  mkdirSync(existing);
  const sentinel = join(existing, 'sentinel');
  writeFileSync(sentinel, 'preserve exact bytes\n');
  const collision = cli('run', '--out', existing);
  assert.equal(collision.status, 1);
  assert.match(collision.stderr, /EEXIST/);
  assert.equal(readFileSync(sentinel, 'utf8'), 'preserve exact bytes\n');
  const link = join(rootDir, 'linked');
  symlinkSync(existing, link);
  const linkedAncestor = cli('run', '--out', join(link, 'new'));
  assert.equal(linkedAncestor.status, 1);
  assert.match(linkedAncestor.stderr, /symbolic links/);
  assert.equal(existsSync(join(existing, 'new')), false);
});

test('CLI rejects a mismatched profile before creating the output', (t) => {
  const temp = temporaryDirectory(t);
  const output = join(temp, 'run');
  const unmatched = join(temp, 'mismatched.json');
  const profile = JSON.parse(readFileSync(profilePath, 'utf8'));
  writeFileSync(unmatched, JSON.stringify({ ...profile, reviewSha256: '0'.repeat(64) }));
  const result = cli('run', '--out', output, '--profile', unmatched);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Profile source binding mismatch/);
  assert.equal(existsSync(output), false);
});

test('CLI rejects invalid Python interpreter overrides before browser work or replay', (t) => {
  const temp = temporaryDirectory(t);
  const output = join(temp, 'run');
  const nonExecutable = join(temp, 'non-executable');
  writeFileSync(nonExecutable, '', { mode: 0o600 });
  const cases = [
    ['run', 'relative-python', /RECONSTRUCTION_PYTHON requires an absolute executable path/],
    ['run', join(temp, 'missing-python'), /RECONSTRUCTION_PYTHON must point to an executable file/],
    ['run', nonExecutable, /RECONSTRUCTION_PYTHON must point to an executable file/],
    ['verify', temp, /RECONSTRUCTION_PYTHON must point to an executable file/],
  ] as const;
  for (const [command, python, message] of cases) {
    const execution = invokeCli([command, '--out', output], {
      ...process.env, RECONSTRUCTION_PYTHON: python, RECONSTRUCTION_CHROMIUM: 'invalid-relative-browser',
    });
    assert.equal(execution.status, 1);
    assert.match(execution.stderr, message);
    assert.equal(execution.stdout, '');
    assert.equal(existsSync(output), false);
  }
});

test('CLI leaves browser startup failures unverified without a relay write', (t) => {
  const output = join(temporaryDirectory(t), 'run');
  const execution = invokeCli(['run', '--out', output], { ...process.env, RECONSTRUCTION_CHROMIUM: 'invalid-relative-browser' });
  assert.equal(execution.status, 1);
  assert.match(execution.stderr, /RECONSTRUCTION_CHROMIUM requires an absolute executable path/);
  const evidence = join(output, 'evidence');
  const pending = parseManifest(JSON.parse(readFileSync(join(evidence, 'manifest.pending.json'), 'utf8')));
  verifyFiles(join(output, 'app'), pending);
  assert.equal(pending.verifiedFunctionality.status, 'unverified');
  const failure = JSON.parse(readFileSync(join(evidence, 'failure.json'), 'utf8'));
  assert.equal(failure.status, 'unverified');
  assert.deepEqual(failure.checks, []);
  assert.deepEqual(failure.relayEffect, { status: 'not_attempted' });
  assert.equal(existsSync(join(evidence, 'verified')), false);
  assert.equal(existsSync(join(evidence, 'partial')), false);
  assert.equal(existsSync(join(output, 'relay-state')), false);
  const verification = cli('verify', '--out', output);
  assert.equal(verification.status, 1);
  assert.match(verification.stderr, /This run is unverified/);
});

test('CLI compares exact pending bytes even when malformed UTF-8 decodes to the same text', (t) => {
  const temp = temporaryDirectory(t);
  const output = join(temp, 'run');
  const profile = writeAttachmentProfile(temp);
  const runArgs = ['--out', output, '--profile', profile];
  const execution = invokeCli(['run', ...runArgs], { ...process.env, RECONSTRUCTION_CHROMIUM: 'invalid-relative-browser' });
  assert.equal(execution.status, 1);
  assert.match(execution.stderr, /requires an absolute executable path/);
  const evidence = join(output, 'evidence');
  rmSync(join(evidence, 'failure.json'));
  const pristine = cli('verify', ...runArgs);
  assert.equal(pristine.status, 1);
  assert.match(pristine.stderr, /ENOENT.*evidence\/verified/);

  const pending = join(evidence, 'manifest.pending.json');
  const original = readFileSync(pending);
  const malformed = replaceWithMalformedByte(original, '�');
  assert.equal(malformed.toString('utf8'), original.toString('utf8'));
  assert.equal(malformed.equals(original), false);
  writeFileSync(pending, malformed);
  const changed = cli('verify', ...runArgs);
  assert.equal(changed.status, 1);
  assert.match(changed.stderr, /Stored pending manifest differs/);
});

test('CLI runs real Chromium and rejects mutated current evidence on replay', { timeout: 180_000 }, (t) => {
  const output = join(temporaryDirectory(t), 'run');
  const result = cli('run', '--out', output);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.verifiedFunctionality, 'verified');
  assert.equal(report.fullAppOutcome, 'HOLD');
  assert.deepEqual(report.heldOutcomes, { liveInference: 'HOLD', pixelParity: 'HOLD', deployment: 'HOLD' });
  assert.equal(report.relay.scope, 'local_artifact_only');

  const evidence = join(output, 'evidence');
  const verified = join(evidence, 'verified');
  const manifestPath = join(verified, 'manifest.json');
  const browserPath = join(verified, 'browser-receipt.json');
  const manifest = parseManifest(JSON.parse(readFileSync(manifestPath, 'utf8')));
  assert.equal(manifest.verifiedFunctionality.status, 'verified');
  assert.deepEqual(report.verifiedChecks, manifest.requiredCheckIds);
  assert.equal(report.verifiedChecks.length, 6);
  const captures = JSON.parse(readFileSync(join(verified, 'captures.json'), 'utf8')).files as Array<{ path: string }>;
  assert.equal(captures.filter(({ path }) => path.endsWith('.png')).length, 12);
  assert.equal(captures.filter(({ path }) => path.endsWith('.webm')).length, 6);
  assert.equal(existsSync(join(evidence, 'failure.json')), false);
  assert.equal(existsSync(join(evidence, 'partial')), false);

  const verify = (...args: string[]) => cli('verify', '--out', output, ...args);
  const requireVerified = () => {
    const verification = verify();
    assert.equal(verification.status, 0, verification.stderr);
    assert.deepEqual(JSON.parse(verification.stdout), report);
  };
  const reject = (pattern: RegExp, ...args: string[]) => {
    const verification = verify(...args);
    assert.equal(verification.status, 1);
    assert.match(verification.stderr, pattern);
  };
  const tamper = (path: string, action: (previous: Buffer) => void, pattern: RegExp) => {
    const previous = readFileSync(path);
    try {
      action(previous);
      reject(pattern);
    } finally {
      writeFileSync(path, previous);
    }
  };

  requireVerified();
  const scriptPath = join(output, 'app', 'app.js');
  tamper(scriptPath, (bytes) => writeFileSync(scriptPath, Buffer.concat([Buffer.from('!'), bytes.subarray(1)])), /Generated file digest mismatch/);
  tamper(scriptPath, () => rmSync(scriptPath), /Missing generated files/);
  tamper(manifestPath, (bytes) => {
    const data = JSON.parse(bytes.toString()) as Manifest;
    data.observedEvidence[0].quote += ' altered';
    writeFileSync(manifestPath, JSON.stringify(data));
  }, /Stored final manifest differs/);
  tamper(browserPath, (bytes) => {
    const data = JSON.parse(bytes.toString());
    data.checks[0].passed = false;
    writeFileSync(browserPath, JSON.stringify(data));
  }, /pass every required check/);
  tamper(browserPath, (bytes) => {
    const data = JSON.parse(bytes.toString());
    data.checks.shift();
    writeFileSync(browserPath, JSON.stringify(data));
  }, /pass every required check/);
  tamper(browserPath, (bytes) => writeFileSync(browserPath, replaceWithMalformedByte(bytes, '×')), /valid for encoding utf-8/i);
  const changedSource = join(output, 'changed-source.json');
  writeFileSync(changedSource, Buffer.concat([readFileSync(sourcePath), Buffer.from('\n')]));
  reject(/Stored pending manifest differs/, '--source', changedSource);
  const changedProfile = join(output, 'changed-profile.json');
  writeFileSync(changedProfile, Buffer.concat([readFileSync(profilePath), Buffer.from('\n')]));
  reject(/capture inventory binding mismatch/, '--profile', changedProfile);
  const capturePath = join(evidence, captures[0].path);
  tamper(capturePath, (bytes) => writeFileSync(capturePath, Buffer.concat([bytes, Buffer.from('altered')])), /capture inventory binding mismatch/);
  const receiptPath = join(verified, 'relay-receipt.json');
  tamper(receiptPath, (bytes) => writeFileSync(receiptPath, Buffer.concat([bytes, Buffer.from('\n')])), /differs from the current harness receipt/);
  const artifactPath = join(output, 'relay-state', 'artifacts', `${report.relay.taskId}.txt`);
  tamper(artifactPath, () => rmSync(artifactPath), /EventRelay|ENOENT/);
  requireVerified();

  const collision = cli('run', '--out', output);
  assert.equal(collision.status, 1);
  assert.match(collision.stderr, /EEXIST/);
  requireVerified();
});

test('CLI runs a real Chromium attachment-only profile and rejects malformed final manifest bytes', { timeout: 180_000 }, (t) => {
  const temp = temporaryDirectory(t);
  const output = join(temp, 'run');
  const options = ['--out', output, '--profile', writeAttachmentProfile(temp)];
  const execution = cli('run', ...options);
  assert.equal(execution.status, 0, execution.stderr);
  assert.deepEqual(JSON.parse(execution.stdout).verifiedChecks, [
    'youtube-attachment', 'invalid-input', 'offline-and-console', 'responsive-light-dark',
  ]);
  const metadata = join(output, 'evidence', 'verified');
  const inventory = JSON.parse(readFileSync(join(metadata, 'captures.json'), 'utf8')).files as Array<{ path: string }>;
  assert.equal(inventory.filter(({ path }) => path.startsWith('screenshots/video-')).length, 6);
  assert.equal(inventory.filter(({ path }) => path.startsWith('screenshots/spatial-')).length, 0);

  const path = join(metadata, 'manifest.json');
  const original = readFileSync(path);
  const malformed = replaceWithMalformedByte(original, '�');
  assert.equal(malformed.toString('utf8'), original.toString('utf8'));
  writeFileSync(path, malformed);
  const replay = cli('verify', ...options);
  assert.equal(replay.status, 1);
  assert.match(replay.stderr, /Stored final manifest differs/);
});

test('CLI preserves the actual relay effect when verified evidence publication fails after Chromium', { timeout: 180_000 }, async (t) => {
  const temp = temporaryDirectory(t);
  const output = join(temp, 'run');
  const evidence = join(output, 'evidence');
  const options = ['--out', output, '--profile', writeAttachmentProfile(temp)];
  const child = spawn(process.execPath, ['--import', 'tsx', cliPath, 'run', ...options], { cwd: root, timeout: 150_000 });
  let stderr = '';
  let stdout = '';
  child.stdout.setEncoding('utf8').on('data', (text: string) => { stdout += text; });
  child.stderr.setEncoding('utf8').on('data', (text: string) => { stderr += text; });
  const exited = new Promise<number | null>((resolve, reject) => {
    child.once('close', resolve);
    child.once('error', reject);
  });
  t.after(() => { if (child.exitCode === null) child.kill(); });
  const pending = join(evidence, 'manifest.pending.json');
  while (!existsSync(pending) && child.exitCode === null && child.signalCode === null) await delay(25, undefined, { signal: t.signal });
  assert.ok(existsSync(pending), stderr);
  const destination = join(evidence, 'verified');
  mkdirSync(destination);
  const sentinel = join(destination, 'sentinel');
  writeFileSync(sentinel, 'preserve after publication error\n');

  assert.equal(await exited, 1, stderr);
  assert.equal(stdout, '');
  assert.match(stderr, /Verified evidence destination already exists/);
  assert.equal(readFileSync(sentinel, 'utf8'), 'preserve after publication error\n');
  for (const file of ['manifest.json', 'browser-receipt.json', 'relay-receipt.json', 'captures.json']) {
    assert.equal(existsSync(join(destination, file)), false);
  }
  const failure = JSON.parse(readFileSync(join(evidence, 'failure.json'), 'utf8'));
  assert.equal(failure.status, 'unverified');
  assert.equal(failure.partialEvidence, 'partial');
  const partial = join(evidence, 'partial');
  const partialManifest = parseManifest(JSON.parse(readFileSync(join(partial, 'manifest.json'), 'utf8')));
  const savedReceipt = readFileSync(join(partial, 'relay-receipt.json'), 'utf8');
  const { receipt } = verifyRelayReceipt(partialManifest, { stateDirectory: join(output, 'relay-state') }, savedReceipt);
  assert.equal(receipt.complete, true);
  assert.deepEqual(failure.relayEffect, { status: 'persisted', taskId: receipt.task_id, evidenceSha256: receipt.evidence.sha256 });
  const replay = cli('verify', ...options);
  assert.equal(replay.status, 1);
  assert.match(replay.stderr, /This run is unverified/);
});
