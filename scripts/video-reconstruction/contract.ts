import { createHash } from 'node:crypto';
import { constants, closeSync, fstatSync, lstatSync, openSync, readFileSync, readdirSync, realpathSync } from 'node:fs';
import { isAbsolute, join, resolve } from 'node:path';
import { z } from 'zod';
import {
  groundedSpecCandidateSchema,
  hashReviewContent,
  inspectGroundedSpec,
  type GroundedBuildSpec,
} from '../../apps/web/src/lib/grounded-build-spec.ts';

const hash = z.string().regex(/^[a-f0-9]{64}$/);
const id = z.string().regex(/^[A-Za-z0-9_-]{1,64}$/);
const videoId = z.string().regex(/^[A-Za-z0-9_-]{11}$/);
const hold = z.literal('HOLD');
const capability = z.enum(['youtube-attachment', 'summary-renderer', 'box-renderer']);
const commonChecks = ['invalid-input', 'offline-and-console', 'responsive-light-dark'] as const;
const checkId = z.enum([...capability.options, ...commonChecks]);

export const profileSchema = z.strictObject({
  id,
  version: z.literal('1'),
  videoId,
  reviewSha256: hash,
  name: z.string().trim().min(1).max(160),
  description: z.string().trim().min(1).max(2000),
  scope: z.literal('scoped-browser-capabilities'),
  fullSourceAcceptance: hold,
  mappings: z.array(z.strictObject({ requirementId: id, capability })).min(1).max(64),
});

const sourceIdentity = z.strictObject({
  packId: z.string().max(100),
  videoId,
  sourceUrl: z.string().max(2048),
  sourceHash: hash,
  rawPackSha256: hash,
  reviewSha256: hash,
});
const evidenceRef = z.strictObject({ kind: z.enum(['transcript', 'visual']), index: z.number().int().min(0).max(10000) });
const seconds = z.number().min(0).max(604800);
const evidenceSchema = evidenceRef.extend({
  requirementId: id,
  videoId,
  startSeconds: seconds,
  endSeconds: seconds,
  quote: z.string().min(1).max(2000),
  text: z.string().min(1),
  provenance: z.literal('source-linked'),
  descriptionType: z.enum(['transcript', 'model-visual-description']),
});
const sourceBlockersSchema = z.strictObject({
  limitations: groundedSpecCandidateSchema.shape.limitations,
  unresolved: groundedSpecCandidateSchema.shape.unresolved,
  unsupported: groundedSpecCandidateSchema.shape.unsupported,
  reviewIssues: z.array(z.strictObject({
    code: z.string(), path: z.string(), message: z.string(), severity: z.enum(['blocking', 'warning']),
  })),
});
const packSchema = z.object({
  version: z.literal('v0'),
  id: z.string(),
  video_id: videoId,
  source_url: z.string(),
  provenance: z.object({ source_hash: hash }),
  grounded_spec: z.unknown(),
  transcript: z.object({ segments: z.array(z.object({ text: z.string() }).loose()).max(10001) }).loose(),
  visual_context: z.object({ visual_elements: z.array(z.object({ content: z.string() }).loose()).max(10001) }).loose().nullish(),
});
const packEnvelope = z.object({ status: z.literal('success'), data: packSchema });

const fileSchema = z.strictObject({
  path: z.string().refine(safeRelativePath, 'Unsafe generated file path'),
  bytes: z.number().int().min(0).max(8 * 1024 * 1024),
  sha256: hash,
});
const filesSchema = z.array(fileSchema).min(1).max(64);
const browserBindingSchema = z.strictObject({
  sourceSha256: hash,
  profileSha256: hash,
  generatedFilesSha256: hash,
  builderRevision: hash,
  pendingManifestSha256: hash,
});
const browserRunSchema = z.strictObject({ runId: id, verifierRevision: hash });
const browserReceiptSchema = browserBindingSchema.extend({
  ...browserRunSchema.shape,
  version: z.literal('video-reconstruction.browser-receipt.v1'),
  checks: z.array(z.strictObject({ id: checkId, passed: z.boolean(), details: z.string().max(2000).optional() })).min(1).max(6),
});

export const manifestSchema = z.strictObject({
  version: z.literal('video-reconstruction.manifest.v1'),
  source: sourceIdentity,
  profile: profileSchema,
  observedEvidence: z.array(evidenceSchema).min(1).max(512),
  inferredArchitecture: z.array(z.strictObject({
    capability,
    requirementId: id,
    rationale: z.string().min(1),
    sourceRefs: z.array(evidenceRef).min(1).max(8),
  })).min(1).max(64),
  generatedCode: z.strictObject({ builderRevision: hash, filesSha256: hash, files: filesSchema }),
  requiredCheckIds: z.array(checkId).min(1).max(6),
  verifiedFunctionality: z.discriminatedUnion('status', [
    z.strictObject({ status: z.literal('unverified') }),
    z.strictObject({ status: z.literal('verified'), receipt: browserReceiptSchema }),
  ]),
  fullAppOutcome: hold,
  heldOutcomes: z.strictObject({ liveInference: hold, pixelParity: hold, deployment: hold }),
  sourceBlockers: sourceBlockersSchema,
});

export type Profile = z.infer<typeof profileSchema>;
export type BrowserCapability = z.infer<typeof capability>;
export type BrowserCheckId = z.infer<typeof checkId>;
export type BrowserReceipt = z.infer<typeof browserReceiptSchema>;
export type Manifest = z.infer<typeof manifestSchema>;
export type GeneratedFile = z.infer<typeof fileSchema>;
export type LoadedSource = {
  identity: z.infer<typeof sourceIdentity>;
  spec: GroundedBuildSpec;
  observedEvidence: z.infer<typeof evidenceSchema>[];
  sourceBlockers: z.infer<typeof sourceBlockersSchema>;
};

export function sha256(value: string | Uint8Array): string {
  return createHash('sha256').update(value).digest('hex');
}

/** Deterministic JSON for validated JSON values, including the relay proposal. */
export function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    return `{${Object.keys(row).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(row[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

export async function loadSource(rawBytes: Uint8Array): Promise<LoadedSource> {
  if (!rawBytes.length || rawBytes.length > 4 * 1024 * 1024) throw new Error('Invalid Video Pack byte length');
  const rawPackSha256 = sha256(rawBytes);
  const value: unknown = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(rawBytes));
  const hasEnvelopeFields = value !== null && typeof value === 'object' && ('status' in value || 'data' in value);
  const pack = hasEnvelopeFields ? packEnvelope.parse(value).data : packSchema.parse(value);
  // Match canonicalIdentityJson without loading the provider and web API modules.
  const sourceHash = sha256(canonicalJson({ version: pack.version, video_id: pack.video_id }));
  if (sourceHash !== pack.provenance.source_hash) throw new Error('Video Pack identity digest mismatch');

  const reviewed = inspectGroundedSpec(pack);
  if (reviewed.status !== 'available') {
    const issues = reviewed.issues.map(({ code, path }) => `${code} ${path}`.trim()).join(', ');
    throw new Error(`Grounded specification ${reviewed.status}${issues ? ` (${issues})` : ''}`);
  }
  const reviewSha256 = await hashReviewContent(reviewed.canonical);
  if (reviewSha256 !== reviewed.contentHash) throw new Error('Grounded review content digest mismatch');

  const observedEvidence = reviewed.spec.requirements.flatMap((requirement) => requirement.citations.map((citation) => {
    const transcript = citation.kind === 'transcript';
    // inspectGroundedSpec already resolved and validated this source row.
    const text = transcript ? pack.transcript.segments[citation.index].text : pack.visual_context!.visual_elements[citation.index].content;
    return evidenceSchema.parse({
      ...citation, requirementId: requirement.id, text, provenance: 'source-linked',
      descriptionType: transcript ? 'transcript' : 'model-visual-description',
    });
  }));
  return {
    identity: { ...reviewed.spec.source, rawPackSha256, reviewSha256 },
    spec: reviewed.spec,
    observedEvidence,
    sourceBlockers: {
      limitations: reviewed.spec.limitations,
      unresolved: reviewed.spec.unresolved,
      unsupported: reviewed.spec.unsupported,
      reviewIssues: reviewed.issues,
    },
  };
}

export function readProfile(value: unknown, source: LoadedSource): Profile {
  const profile = profileSchema.parse(value);
  if (profile.videoId !== source.identity.videoId || profile.reviewSha256 !== source.identity.reviewSha256) {
    throw new Error('Profile source binding mismatch');
  }
  const pairs = new Set<string>();
  for (const mapping of profile.mappings) {
    const { requirementId, capability } = mapping;
    const key = `${requirementId}:${capability}`;
    if (pairs.has(key)) throw new Error(`Duplicate profile mapping ${key}`);
    pairs.add(key);
    const requirement = source.spec.requirements.find((entry) => entry.id === requirementId);
    if (!requirement?.citations.some((citation) => citation.kind === 'transcript')) {
      throw new Error(`Profile mapping requires a source requirement with a transcript citation: ${requirementId}`);
    }
  }
  return profile;
}

const architectureRationale: Record<BrowserCapability, string> = {
  'youtube-attachment': 'A local URL field and removable attachment represent the cited media prompt workflow.',
  'summary-renderer': 'A local renderer presents structured summary data supplied by the user.',
  'box-renderer': 'A local image overlay presents normalized bounding boxes supplied by the user.',
};

function requiredChecks(profile: Profile): BrowserCheckId[] {
  return [...new Set(profile.mappings.map((mapping) => mapping.capability)), ...commonChecks];
}

export function createManifest(
  source: LoadedSource,
  value: Profile,
  generated: { builderRevision: string; files: Readonly<Record<string, Uint8Array | string>> },
): Manifest {
  const profile = readProfile(value, source);
  const files = fileLayout(Object.keys(generated.files).sort().map((path) => {
    const data = generated.files[path];
    const bytes = typeof data === 'string' ? Buffer.from(data, 'utf8') : data;
    return { path, bytes: bytes.byteLength, sha256: sha256(bytes) };
  })).files;
  return manifestSchema.parse({
    version: 'video-reconstruction.manifest.v1',
    source: source.identity,
    profile,
    observedEvidence: source.observedEvidence,
    inferredArchitecture: profile.mappings.map(({ requirementId, capability }) => ({
      requirementId, capability, rationale: architectureRationale[capability],
      sourceRefs: source.observedEvidence.filter((entry) => entry.requirementId === requirementId).map(({ kind, index }) => ({ kind, index })),
    })),
    generatedCode: { builderRevision: generated.builderRevision, filesSha256: sha256(canonicalJson(files)), files },
    requiredCheckIds: requiredChecks(profile),
    verifiedFunctionality: { status: 'unverified' },
    fullAppOutcome: 'HOLD',
    heldOutcomes: { liveInference: 'HOLD', pixelParity: 'HOLD', deployment: 'HOLD' },
    sourceBlockers: source.sourceBlockers,
  });
}

function safeRelativePath(path: string): boolean {
  return path.length <= 240 && path.split('/').every((part) =>
    /^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(part) && !part.endsWith('.') &&
    !/^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part));
}

function fileLayout(entries: readonly GeneratedFile[]) {
  const files = filesSchema.parse(entries);
  const paths = new Map<string, string>();
  const directories = new Set<string>();
  const expected = new Map<string, GeneratedFile>();
  for (const file of files) {
    if (expected.has(file.path)) throw new Error(`Duplicate generated path: ${file.path}`);
    expected.set(file.path, file);
    const parts = file.path.split('/');
    for (let count = 1; count <= parts.length; count++) {
      const path = parts.slice(0, count).join('/');
      const key = path.toLowerCase();
      if (paths.has(key) && paths.get(key) !== path) throw new Error(`Conflicting generated path: ${path}`);
      paths.set(key, path);
      if (count < parts.length) directories.add(path);
    }
  }
  if ([...directories].some((path) => expected.has(path))) throw new Error('Generated file and directory paths conflict');
  return { files, directories, expected };
}

export function validateFiles(directory: string, entries: readonly GeneratedFile[]): GeneratedFile[] {
  const { files, directories, expected } = fileLayout(entries);
  if (!isAbsolute(directory) || realpathSync(directory) !== resolve(directory) || !lstatSync(directory).isDirectory()) {
    throw new Error('Generated file root must be an absolute directory without symlinks');
  }
  function visit(relativeDirectory: string): void {
    for (const name of readdirSync(join(directory, relativeDirectory))) {
      const relativePath = relativeDirectory ? `${relativeDirectory}/${name}` : name;
      const path = join(directory, relativePath);
      const unsafePath = `Unexpected or unsafe generated path: ${relativePath}`;
      if (directories.has(relativePath)) {
        if (!lstatSync(path).isDirectory()) throw new Error(unsafePath);
        visit(relativePath);
        continue;
      }
      const file = expected.get(relativePath);
      if (!file) throw new Error(unsafePath);
      let fd: number;
      try {
        fd = openSync(path, constants.O_RDONLY | constants.O_NOFOLLOW | constants.O_NONBLOCK);
      } catch (error) {
        if (error instanceof Error && 'code' in error && error.code === 'ELOOP') throw new Error(unsafePath, { cause: error });
        throw error;
      }
      try {
        const opened = fstatSync(fd);
        if (!opened.isFile()) throw new Error(unsafePath);
        if (opened.nlink !== 1 || opened.size !== file.bytes) {
          throw new Error(`Generated file byte count or type mismatch: ${relativePath}`);
        }
        const bytes = readFileSync(fd);
        if (bytes.length !== file.bytes || sha256(bytes) !== file.sha256) {
          throw new Error(`Generated file digest mismatch: ${relativePath}`);
        }
      } finally {
        closeSync(fd);
      }
      expected.delete(relativePath);
    }
  }
  visit('');
  if (expected.size) throw new Error(`Missing generated files: ${[...expected.keys()].join(', ')}`);
  return files;
}

export function verifyFiles(directory: string, manifest: Manifest): void {
  const files = validateFiles(directory, manifest.generatedCode.files);
  if (sha256(canonicalJson(files)) !== manifest.generatedCode.filesSha256) throw new Error('Generated files digest mismatch');
}

export function browserBindings(manifest: Manifest): z.infer<typeof browserBindingSchema> {
  const { verifiedFunctionality: _verification, ...pendingManifest } = manifest;
  return {
    sourceSha256: sha256(canonicalJson(manifest.source)),
    profileSha256: sha256(canonicalJson(profileSchema.parse(manifest.profile))),
    generatedFilesSha256: manifest.generatedCode.filesSha256,
    builderRevision: manifest.generatedCode.builderRevision,
    pendingManifestSha256: sha256(canonicalJson(pendingManifest)),
  };
}

/** The operator owns the verifier code and run state. A receipt imported from an
 * untrusted source is never proof, even if its structure and bindings match. */
export function finalizeManifest(manifest: Manifest, value: unknown, expectedRun: z.infer<typeof browserRunSchema>): Manifest {
  const pending = parseManifest(manifest);
  if (pending.verifiedFunctionality.status !== 'unverified') throw new Error('Manifest is already verified');
  const receipt = browserReceiptSchema.parse(value);
  validateBrowserReceipt(pending, receipt, browserRunSchema.parse(expectedRun));
  return { ...pending, verifiedFunctionality: { status: 'verified', receipt } };
}

function validateBrowserReceipt(manifest: Manifest, receipt: BrowserReceipt, expectedRun?: z.infer<typeof browserRunSchema>): void {
  const bindings = { ...browserBindings(manifest), ...expectedRun };
  for (const field of Object.keys(bindings) as Array<keyof typeof bindings>) {
    if (receipt[field] !== bindings[field]) throw new Error(`Browser receipt binding mismatch: ${field}`);
  }
  const checks = new Map(receipt.checks.map(({ id, passed }) => [id, passed]));
  const required = manifest.requiredCheckIds;
  if (checks.size !== receipt.checks.length || checks.size !== required.length || required.some((id) => checks.get(id) !== true)) {
    throw new Error('Browser receipt must pass every required check exactly once');
  }
}

/** Validate structure and internal bindings. Use trusted run evidence for proof. */
export function parseManifest(value: unknown): Manifest {
  const manifest = manifestSchema.parse(value);
  if (manifest.profile.videoId !== manifest.source.videoId || manifest.profile.reviewSha256 !== manifest.source.reviewSha256) {
    throw new Error('Profile source binding mismatch');
  }
  if (canonicalJson(requiredChecks(manifest.profile)) !== canonicalJson(manifest.requiredCheckIds)) {
    throw new Error('Required browser checks mismatch');
  }
  const { files } = fileLayout(manifest.generatedCode.files);
  if (sha256(canonicalJson(files)) !== manifest.generatedCode.filesSha256) throw new Error('Generated files digest mismatch');
  if (manifest.verifiedFunctionality.status === 'verified') {
    validateBrowserReceipt(manifest, manifest.verifiedFunctionality.receipt);
  }
  return manifest;
}

export function serializeManifest(manifest: Manifest): string {
  return `${JSON.stringify(parseManifest(manifest), null, 2)}\n`;
}

/** JSON Schema describes the shape. Use parseManifest for runtime bindings. */
export function exportManifestJsonSchema() {
  return z.toJSONSchema(manifestSchema);
}
