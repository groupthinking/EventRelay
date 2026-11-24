import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, unlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { hashReviewContent, inspectGroundedSpec } from '../apps/web/src/lib/grounded-build-spec.ts';
import {
  browserBindings, createManifest, exportManifestJsonSchema, finalizeManifest, loadSource, parseManifest, readProfile, serializeManifest, sha256, verifyFiles,
  type BrowserReceipt, type LoadedSource, type Manifest, type Profile,
} from '../scripts/video-reconstruction/contract.ts';
import { persistManifest, verifyRelayReceipt } from '../scripts/video-reconstruction/relay.ts';

const raw = readFileSync(new URL('../apps/web/src/lib/sample-pack/auJzb1D-fag.pack.json', import.meta.url));
const encode = (value: unknown) => Buffer.from(JSON.stringify(value));
const pack = () => JSON.parse(raw.toString('utf8'));
const generated = {
  builderRevision: sha256('test builder revision'),
  files: { 'index.html': '<p>Explicit test fixture</p>\n', 'assets/app.js': Buffer.from('"use strict";\n') },
};
const run = { runId: 'test-run', verifierRevision: sha256('test verifier revision') };

function profileData(source: LoadedSource): Profile {
  return {
    id: 'sample-profile',
    version: '1',
    videoId: source.identity.videoId,
    reviewSha256: source.identity.reviewSha256,
    name: 'Browser capabilities',
    description: 'Scoped capabilities for the retained Video Pack.',
    scope: 'scoped-browser-capabilities',
    fullSourceAcceptance: 'HOLD',
    mappings: [
      { requirementId: 'G-REQ-01', capability: 'youtube-attachment' },
      { requirementId: 'G-REQ-02', capability: 'summary-renderer' },
      { requirementId: 'G-REQ-03', capability: 'box-renderer' },
    ],
  };
}

async function fixture() {
  const source = await loadSource(raw);
  const profile = readProfile(profileData(source), source);
  return { source, profile, manifest: createManifest(source, profile, generated) };
}

function browserReceipt(manifest: Manifest): BrowserReceipt {
  return {
    version: 'video-reconstruction.browser-receipt.v1',
    ...browserBindings(manifest),
    ...run,
    checks: manifest.requiredCheckIds.map((id) => ({ id, passed: true })),
  };
}

test('actual sample preserves exact cited rows, digest identities, provenance, and blockers', async () => {
  const { source, manifest } = await fixture();
  const data = pack().data;
  assert.equal(source.identity.videoId, 'auJzb1D-fag');
  assert.equal(source.identity.sourceHash, data.provenance.source_hash);
  assert.equal(source.identity.reviewSha256, data.grounded_spec.contentHash);
  assert.equal(source.identity.rawPackSha256, sha256(raw));
  assert.notEqual(source.identity.rawPackSha256, source.identity.sourceHash);
  assert.equal(source.observedEvidence.length, 6);
  for (const evidence of manifest.observedEvidence) {
    const { index, startSeconds, endSeconds, text, quote } = evidence;
    assert.equal(evidence.provenance, 'source-linked');
    assert.ok(text.includes(quote));
    if (evidence.kind === 'visual') {
      const row = data.visual_context.visual_elements[index];
      assert.equal(evidence.descriptionType, 'model-visual-description');
      assert.deepEqual([startSeconds, endSeconds, text], [row.timestamp, row.timestamp, row.content]);
    } else {
      const row = data.transcript.segments[index];
      assert.equal(evidence.descriptionType, 'transcript');
      assert.deepEqual([startSeconds, endSeconds, text], [row.start_s, row.end_s, row.text]);
    }
  }
  assert.equal(manifest.fullAppOutcome, 'HOLD');
  assert.deepEqual(manifest.heldOutcomes, { liveInference: 'HOLD', pixelParity: 'HOLD', deployment: 'HOLD' });
  assert.deepEqual(manifest.sourceBlockers.unsupported, source.spec.unsupported);
  assert.deepEqual(manifest.sourceBlockers.unresolved, source.spec.unresolved);
  assert.deepEqual(manifest.sourceBlockers.limitations, source.spec.limitations);
  assert.ok(manifest.sourceBlockers.reviewIssues.some(({ path, severity }) => path === 'unsupported.UNSUPP-01' && severity === 'blocking'));
  assert.ok(manifest.sourceBlockers.reviewIssues.some(({ path }) => path === 'unresolved.UNRES-01'));
  assert.deepEqual(manifest.verifiedFunctionality, { status: 'unverified' });
  assert.deepEqual(manifest.inferredArchitecture.map(({ sourceRefs }) => sourceRefs.length), [2, 2, 2]);
  const schema = exportManifestJsonSchema();
  assert.equal(schema.$schema, 'https://json-schema.org/draft/2020-12/schema');
  assert.partialDeepStrictEqual(schema.properties?.fullAppOutcome, { const: 'HOLD' });
});

test('bare pack works and any raw byte change alters the source binding', async () => {
  const { source, manifest, profile } = await fixture();
  const bare = await loadSource(encode(pack().data));
  assert.equal(bare.identity.reviewSha256, source.identity.reviewSha256);
  assert.notEqual(bare.identity.rawPackSha256, source.identity.rawPackSha256);
  const newManifest = createManifest(bare, profile, generated);
  assert.throws(() => finalizeManifest(newManifest, browserReceipt(manifest), run), /sourceSha256/);
});

test('explicit response envelope fields prevent fallback to a valid bare pack', async () => {
  const { data } = pack();
  await assert.rejects(loadSource(encode({ ...data, status: 'error', data })), /"status"/);
  await assert.rejects(loadSource(encode({ ...data, status: 'success', data: {} })), /video_id/);
  await assert.rejects(loadSource(encode({ ...data, data })), /"status"/);
});

test('stored identity, bound identity, review content and citation tampering fail closed', async () => {
  const wrongHash = pack();
  wrongHash.data.provenance.source_hash = wrongHash.data.grounded_spec.spec.source.sourceHash = '0'.repeat(64);
  await assert.rejects(loadSource(encode(wrongHash)), /identity digest mismatch/);

  const wrongIdentity = pack();
  wrongIdentity.data.grounded_spec.spec.source.sourceUrl += '&test=true';
  await assert.rejects(loadSource(encode(wrongIdentity)), /Grounded specification invalid/);

  const wrongReview = pack();
  wrongReview.data.grounded_spec.spec.app.name += ' altered';
  await assert.rejects(loadSource(encode(wrongReview)), /review content digest mismatch/);

  const wrongCitation = pack();
  wrongCitation.data.grounded_spec.spec.requirements[0].citations[0].startSeconds++;
  await assert.rejects(loadSource(encode(wrongCitation)), /invalid-citation/);

  const wrongEvidence = pack();
  wrongEvidence.data.transcript.segments[30].text += ' Appended content.';
  await assert.rejects(loadSource(encode(wrongEvidence)), /review content digest mismatch/);
});

test('profiles restrict fields, binding, capabilities, and source-linked transcript requirements', async () => {
  const { source, profile } = await fixture();
  assert.throws(() => readProfile({ ...profile, command: 'arbitrary' }, source));
  assert.throws(() => readProfile({ ...profile, scope: 'complete-app' }, source));
  assert.throws(() => readProfile({ ...profile, reviewSha256: '0'.repeat(64) }, source), /binding mismatch/);
  assert.throws(() => readProfile({ ...profile, videoId: 'AAAAAAAAAAA' }, source), /binding mismatch/);
  const invalidMapping = (requirementId: string, capability: string) => ({ ...profile, mappings: [{ requirementId, capability }] });
  assert.throws(() => readProfile(invalidMapping('G-REQ-01', 'run-model'), source));
  assert.throws(() => readProfile(invalidMapping('unknown', 'box-renderer'), source), /requires a source requirement/);
  assert.throws(() => readProfile({ ...profile, mappings: [profile.mappings[0], profile.mappings[0]] }, source), /Duplicate/);

  const visualOnly = pack();
  visualOnly.data.grounded_spec.spec.requirements[0].citations.shift();
  const inspection = inspectGroundedSpec(visualOnly.data);
  assert.equal(inspection.status, 'available');
  visualOnly.data.grounded_spec.contentHash = await hashReviewContent(inspection.canonical);
  const sourceWithVisualOnlyRequirement = await loadSource(encode(visualOnly));
  const profileForVisualOnlySource = profileData(sourceWithVisualOnlyRequirement);
  assert.throws(() => readProfile(profileForVisualOnlySource, sourceWithVisualOnlyRequirement), /transcript citation: G-REQ-01/);

  const smallProfile = readProfile({ ...profile, mappings: [profile.mappings[1]] }, source);
  const scoped = createManifest(source, smallProfile, generated);
  assert.deepEqual(scoped.requiredCheckIds, ['summary-renderer', 'invalid-input', 'offline-and-console', 'responsive-light-dark']);
});

test('file paths must be portable, unambiguous relative file names', async () => {
  const { source, profile } = await fixture();
  for (const path of ['../escape.js', '/absolute.js', 'a//b.js', 'a/./b.js', 'a\\b.js', 'C:drive.js', 'aux.js', 'file.js.']) {
    assert.throws(() => createManifest(source, profile, { ...generated, files: { [path]: '' } }), /Unsafe generated file path/);
  }
  assert.throws(() => createManifest(source, profile, { ...generated, files: {} }));
  assert.throws(() => createManifest(source, profile, { ...generated, files: { 'Upper/a': '', 'upper/b': '' } }), /Conflicting generated path/);
  assert.throws(() => createManifest(source, profile, { ...generated, files: { a: '', 'a/b': '' } }), /file and directory paths conflict/);
});

test('file verification reads actual bytes and rejects missing, extra and linked files', async (t) => {
  const { manifest } = await fixture();
  const temp = mkdtempSync(join(tmpdir(), 'uvai-reconstruction-files-'));
  t.after(() => rmSync(temp, { force: true, recursive: true }));
  mkdirSync(join(temp, 'assets'));
  for (const [path, contents] of Object.entries(generated.files)) writeFileSync(join(temp, path), contents);
  verifyFiles(temp, manifest);
  assert.throws(() => verifyFiles(temp, { ...manifest, generatedCode: { ...manifest.generatedCode, filesSha256: '0'.repeat(64) } }), /Generated files digest mismatch/);

  const html = join(temp, 'index.html');
  writeFileSync(html, generated.files['index.html'].replace('Explicit', 'Altered!'));
  assert.throws(() => verifyFiles(temp, manifest), /file digest mismatch: index.html/);
  unlinkSync(html);
  assert.throws(() => verifyFiles(temp, manifest), /Missing generated files: index.html/);
  symlinkSync(join(temp, 'assets/app.js'), html);
  assert.throws(() => verifyFiles(temp, manifest), /unsafe generated path: index.html/);
  unlinkSync(html);
  writeFileSync(html, generated.files['index.html']);
  writeFileSync(join(temp, 'unexpected.js'), '');
  assert.throws(() => verifyFiles(temp, manifest), /Unexpected or unsafe generated path/);
});

test('browser results must match the trusted run and pass every required check', async () => {
  const { manifest } = await fixture();
  const receipt = browserReceipt(manifest);
  for (const value of [null, {}, { ...receipt, checks: [] }, { ...receipt, extra: true }]) {
    assert.throws(() => finalizeManifest(manifest, value, run));
  }
  for (const field of ['sourceSha256', 'profileSha256', 'generatedFilesSha256', 'builderRevision', 'pendingManifestSha256', 'runId', 'verifierRevision'] as const) {
    assert.throws(() => finalizeManifest(manifest, { ...receipt, [field]: '0'.repeat(64) }, run), new RegExp(field));
  }
  const [first, ...rest] = receipt.checks;
  for (const checks of [[...rest], [...rest, rest[0]], [{ ...first, passed: false }, ...rest]]) {
    assert.throws(() => finalizeManifest(manifest, { ...receipt, checks }, run), /pass every required check exactly once/);
  }
  assert.throws(() => finalizeManifest({ ...manifest, requiredCheckIds: ['box-renderer'] }, receipt, run), /Required browser checks mismatch/);
  const final = finalizeManifest(manifest, receipt, run);
  assert.deepEqual(final.verifiedFunctionality, { status: 'verified', receipt });
  assert.equal(final.fullAppOutcome, 'HOLD');
  assert.deepEqual(final.heldOutcomes, manifest.heldOutcomes);
  assert.deepEqual(final.sourceBlockers, manifest.sourceBlockers);
  assert.throws(() => finalizeManifest(final, receipt, run), /already verified/);
  assert.throws(() => parseManifest({
    ...final, verifiedFunctionality: { status: 'verified', receipt: { ...receipt, sourceSha256: '0'.repeat(64) } },
  }), /sourceSha256/);
  assert.throws(() => parseManifest({ ...final, fullAppOutcome: 'PASS' }));
});

test('browser receipt rejects changes to evidence, architecture, or blockers before and after finalization', async () => {
  const { manifest } = await fixture();
  const receipt = browserReceipt(manifest);
  const final = finalizeManifest(manifest, receipt, run);
  assert.deepEqual(parseManifest(final), final);
  assert.deepEqual(browserBindings(final), browserBindings(manifest));

  const edits: Array<[string, (value: Manifest) => void]> = [
    ['citation quote', (value) => { value.observedEvidence[0].quote += ' Changed.'; }],
    ['architecture rationale', (value) => { value.inferredArchitecture[0].rationale += ' Changed.'; }],
    ['architecture source refs', (value) => { value.inferredArchitecture[0].sourceRefs.shift(); }],
    ['unsupported capabilities', (value) => { value.sourceBlockers.unsupported = []; }],
    ['unresolved requirements', (value) => { value.sourceBlockers.unresolved = []; }],
  ];
  for (const [label, edit] of edits) {
    const pendingEdit = structuredClone(manifest);
    const finalEdit = structuredClone(final);
    edit(pendingEdit);
    edit(finalEdit);
    assert.throws(() => finalizeManifest(pendingEdit, receipt, run), /pendingManifestSha256/, `Pending ${label}`);
    assert.throws(() => parseManifest(finalEdit), /pendingManifestSha256/, `Final ${label}`);
  }
});

test('real EventRelay round trip is exact, idempotent and scoped to manifest persistence', async (t) => {
  const { source, profile, manifest } = await fixture();
  const temp = mkdtempSync(join(tmpdir(), 'uvai-reconstruction-relay-'));
  t.after(() => rmSync(temp, { force: true, recursive: true }));
  const options = { stateDirectory: join(temp, 'relay') };
  const final = finalizeManifest(manifest, browserReceipt(manifest), run);
  const result = persistManifest(final, options);
  const { receipt, rawReceipt } = result;
  assert.equal(receipt.scope, 'local_artifact_only');
  assert.equal(receipt.complete, true);
  assert.equal(receipt.external_task_complete, false);
  assert.equal(receipt.attempts, 1);
  const artifact = join(options.stateDirectory, receipt.evidence.artifact);
  assert.equal(readFileSync(artifact, 'utf8'), serializeManifest(final));
  assert.deepEqual(persistManifest(final, options), result);
  assert.deepEqual(verifyRelayReceipt(final, options, rawReceipt), result);
  assert.throws(() => verifyRelayReceipt(final, options, ''), /differs from the current harness receipt/);
  assert.throws(() => verifyRelayReceipt(final, options, rawReceipt.replace(receipt.task_id, '0'.repeat(32))), /differs from the current harness receipt/);
  assert.throws(() => verifyRelayReceipt(final, options, rawReceipt.replace(receipt.contract_hash, '0'.repeat(64))), /differs from the current harness receipt/);
  assert.throws(() => verifyRelayReceipt(final, options, rawReceipt.replace(receipt.evidence.sha256, '0'.repeat(64))), /differs from the current harness receipt/);
  assert.throws(() => verifyRelayReceipt(manifest, options, rawReceipt), /Unknown task/);

  const changed = createManifest(source, { ...profile, description: 'Changed profile 🚀' }, generated);
  assert.throws(() => verifyRelayReceipt(changed, options, rawReceipt), /Unknown task/);
  const changedResult = persistManifest(changed, options);
  assert.notEqual(changedResult.receipt.task_id, receipt.task_id);
  assert.throws(() => verifyRelayReceipt(changed, options, rawReceipt), /differs from the current harness receipt/);
});

test('real EventRelay replay rejects deleted or modified manifest artifacts', async (t) => {
  const { manifest } = await fixture();
  const temp = mkdtempSync(join(tmpdir(), 'uvai-reconstruction-relay-tamper-'));
  t.after(() => rmSync(temp, { force: true, recursive: true }));
  for (const operation of ['delete', 'tamper']) {
    const options = { stateDirectory: join(temp, operation) };
    const result = persistManifest(manifest, options);
    const artifact = join(options.stateDirectory, result.receipt.evidence.artifact);
    if (operation === 'delete') unlinkSync(artifact);
    else writeFileSync(artifact, serializeManifest(manifest).replace('unverified', 'verified  '));
    assert.throws(() => verifyRelayReceipt(manifest, options, result.rawReceipt), /receipt failed \(2\)/);
    assert.throws(() => persistManifest(manifest, options), /run failed \(2\)/);
  }
});
