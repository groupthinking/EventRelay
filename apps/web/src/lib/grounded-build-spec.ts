import { z } from 'zod';

const text = z.string().trim().max(2000);
const label = z.string().trim().max(160);
const id = z.string().regex(/^[a-zA-Z0-9_-]{1,64}$/);
const hash = z.string().regex(/^[a-f0-9]{64}$/);
const seconds = z.number().finite().min(0).max(604800);
const videoIdSchema = z.string().regex(/^[a-zA-Z0-9_-]{11}$/);
const list = <T extends z.ZodTypeAny>(schema: T) => z.array(schema).max(64);
const capability = z.enum(['browser-ui', 'local-state', 'local-persistence', 'server', 'accounts', 'shared-database', 'payments', 'secrets', 'native', 'background', 'unknown']);
const citationSchema = z.object({
  kind: z.enum(['transcript', 'visual']), index: z.number().int().min(0).max(10000),
  videoId: videoIdSchema, startSeconds: seconds, endSeconds: seconds, quote: text.min(1),
}).strict().refine((ref) => ref.endSeconds >= ref.startSeconds, 'Reversed citation timestamps');
const honestySchema = z.object({
  version: z.literal('1'), outputClass: z.literal('browser-interactive'),
  sourceStatus: z.enum(['full', 'partial', 'none']), confidence: z.number().finite().min(0).max(1),
  limitations: list(text.min(1)),
});
export const groundedSpecCandidateSchema = honestySchema.extend({
  app: z.object({ name: label, purpose: text }).strict(),
  screens: list(z.object({ id, name: label.min(1), purpose: text }).strict()),
  state: list(z.object({ id, name: label.min(1), description: text, persistence: z.enum(['memory', 'local', 'unknown']) }).strict()),
  requirements: list(z.object({
    id, screenId: id, title: label.min(1), detail: text,
    classification: z.enum(['observed', 'inferred', 'proposed', 'unknown']), required: z.boolean(),
    capabilities: z.array(capability).min(1).max(11), rationale: text,
    citations: z.array(citationSchema).max(8),
  }).strict()),
  acceptanceCriteria: list(z.object({ id, requirementId: id, given: text.min(1), when: text.min(1), then: text.min(1) }).strict()),
  unresolved: list(z.object({ id, requirementIds: list(id), question: text.min(1), required: z.boolean() }).strict()),
  unsupported: list(z.object({ id, requirementIds: list(id), capability, reason: text.min(1), required: z.boolean() }).strict()),
}).strict();
const sourceSchema = z.object({ packId: z.string().max(100), videoId: videoIdSchema, sourceUrl: z.string().max(2048), sourceHash: hash }).strict();
const boundSchema = groundedSpecCandidateSchema.extend({ source: sourceSchema });
const issueSchema = z.object({ code: z.string().max(80), path: z.string().max(240), message: z.string().max(500), severity: z.enum(['blocking', 'warning']) }).strict();
const diagnosticSchema = z.object({ status: z.enum(['invalid', 'source-unavailable']), issues: z.array(issueSchema).min(1).max(200) }).strict();
const recordSchema = z.union([diagnosticSchema, z.object({ status: z.literal('available'), spec: boundSchema, contentHash: hash }).strict()]);

export type SpecIssue = z.infer<typeof issueSchema>;
export type GroundedSpecCandidate = z.infer<typeof groundedSpecCandidateSchema>;
export type GroundedBuildSpec = z.infer<typeof boundSchema>;
export type GroundedSpecRecord = z.infer<typeof recordSchema>;
export type GroundedSpecExtraction = z.infer<typeof diagnosticSchema> | { status: 'available'; spec: GroundedSpecCandidate };
export type ReviewInspection = { status: 'unavailable' | 'invalid' | 'source-unavailable'; issues: SpecIssue[] } | {
  status: 'available'; spec: GroundedBuildSpec; contentHash: string; canonical: string; issues: SpecIssue[];
};
export type SpecEvidence = { transcript?: unknown; visual_context?: unknown };

function issue(code: string, message: string, path = '', severity: SpecIssue['severity'] = 'blocking'): SpecIssue {
  return { code, path, message, severity };
}
export function invalidGroundedSpec(message: string): GroundedSpecRecord & { status: 'invalid' } {
  return { status: 'invalid', issues: [issue('invalid-specification', message)] };
}
function shapeIssues(error: z.ZodError): SpecIssue[] {
  return error.issues.slice(0, 64).map((item) => issue('invalid-shape', item.message.slice(0, 500), item.path.join('.').slice(0, 240)));
}
const transcriptRows = z.object({ segments: z.array(z.unknown()).max(10001) });
const visualRows = z.object({ visual_elements: z.array(z.unknown()).max(10001) });
const transcriptRow = z.object({ idx: z.number().int().nonnegative(), start_s: seconds, end_s: seconds, text: z.string().trim().min(1).max(20000) }).refine((row) => row.end_s >= row.start_s);
const visualRow = z.object({ timestamp: seconds, content: z.string().trim().min(1).max(20000) });

function resolveCitation(ref: GroundedSpecCandidate['requirements'][number]['citations'][number], evidence: SpecEvidence) {
  if (ref.kind === 'transcript') {
    const rows = transcriptRows.safeParse(evidence.transcript);
    const row = transcriptRow.safeParse(rows.success ? rows.data.segments[ref.index] : undefined);
    if (!row.success || ref.startSeconds !== row.data.start_s || ref.endSeconds !== row.data.end_s || !row.data.text.includes(ref.quote)) return null;
    return { kind: ref.kind, index: ref.index, ...row.data };
  }
  const rows = visualRows.safeParse(evidence.visual_context);
  const row = visualRow.safeParse(rows.success ? rows.data.visual_elements[ref.index] : undefined);
  if (!row.success || ref.startSeconds !== row.data.timestamp || ref.endSeconds !== row.data.timestamp || !row.data.content.includes(ref.quote)) return null;
  return { kind: ref.kind, index: ref.index, ...row.data };
}

export function parseGroundedSpec(value: unknown, evidence: SpecEvidence, videoId: string, recovered = false): GroundedSpecExtraction | undefined {
  if (recovered) return invalidGroundedSpec('Recovered or truncated JSON cannot establish a complete grounded specification.');
  if (value === undefined) return undefined;
  const honesty = honestySchema.safeParse(value);
  if (!honesty.success) return { status: 'invalid', issues: shapeIssues(honesty.error) };
  if (honesty.data.sourceStatus === 'none') return {
    status: 'source-unavailable', issues: [issue('no-source', 'No usable source was reported. Provide a usable video; no blueprint was produced.')],
  };
  const parsed = groundedSpecCandidateSchema.safeParse(value);
  if (!parsed.success) return { status: 'invalid', issues: shapeIssues(parsed.error) };
  const spec = parsed.data;
  const issues: SpecIssue[] = [];
  for (const [key, rows] of Object.entries({ screens: spec.screens, state: spec.state, requirements: spec.requirements, acceptanceCriteria: spec.acceptanceCriteria, unresolved: spec.unresolved, unsupported: spec.unsupported })) {
    if (new Set(rows.map((row) => row.id)).size !== rows.length) issues.push(issue('duplicate-id', 'IDs must be unique within each collection.', key));
  }
  const screens = new Set(spec.screens.map((row) => row.id));
  const requirements = new Set(spec.requirements.map((row) => row.id));
  let references = 0;
  for (const req of spec.requirements) {
    if (!screens.has(req.screenId)) issues.push(issue('dangling-screen', 'Requirement refers to an absent screen.', req.id));
    if (req.classification === 'observed' && req.citations.length === 0) issues.push(issue('missing-citation', 'Observed requirement needs source evidence.', req.id));
    if ((req.classification === 'inferred' || req.classification === 'proposed') && !req.rationale) issues.push(issue('missing-rationale', 'Inferred or proposed choices require an explicit rationale.', req.id));
    for (const ref of req.citations) {
      references++;
      if (ref.videoId !== videoId || !resolveCitation(ref, evidence)) issues.push(issue('invalid-citation', 'Citation must match this video, an existing source row, its timestamps and supporting text.', req.id));
    }
  }
  for (const row of spec.acceptanceCriteria) {
    if (!requirements.has(row.requirementId)) issues.push(issue('dangling-requirement', 'Acceptance criterion refers to an absent requirement.', row.id));
  }
  for (const row of [...spec.unresolved, ...spec.unsupported]) {
    if (row.requirementIds.some((ref) => !requirements.has(ref))) issues.push(issue('dangling-requirement', 'Question or capability refers to an absent requirement.', row.id));
  }
  if (references === 0) issues.push(issue('missing-evidence', 'No source-linked application requirements are available. Do not infer an app from a title or URL.'));
  return issues.length ? { status: 'invalid', issues: issues.slice(0, 200) } : { status: 'available', spec };
}

export function specificationIssues(spec: GroundedBuildSpec): SpecIssue[] {
  const issues: SpecIssue[] = [issue('model-evidence', 'Source-linked, not independently verified. Visual observations are model descriptions, not verified captured frames.', '', 'warning')];
  if (spec.sourceStatus === 'partial') issues.push(issue('partial-source', 'Source coverage is partial.', '', 'warning'));
  if (spec.confidence < 0.7) issues.push(issue('low-confidence', 'Model-reported confidence is below 70%.'));
  if (!spec.app.name || !spec.app.purpose) issues.push(issue('missing-purpose', 'Application name and purpose are required.'));
  if (!spec.screens.length || !spec.requirements.length) issues.push(issue('missing-interaction', 'Identifiable screens and interactive requirements are required.'));
  if (spec.state.some((row) => row.persistence === 'unknown')) issues.push(issue('unknown-state', 'Browser state persistence is unresolved.'));
  const browser = new Set(['browser-ui', 'local-state', 'local-persistence']);
  for (const req of spec.requirements) {
    const severity = req.required ? 'blocking' : 'warning';
    if (req.classification !== 'observed') issues.push(issue('unresolved-choice', 'This choice is not observed; acknowledgment does not accept it.', req.id, severity));
    if (req.capabilities.some((value) => !browser.has(value))) issues.push(issue('unsupported-capability', `Outside browser-only scope: ${req.capabilities.filter((value) => !browser.has(value)).join(', ')}. No local substitute is authorized.`, req.id, severity));
    if (!spec.acceptanceCriteria.some((row) => row.requirementId === req.id)) issues.push(issue('missing-criterion', 'Requirement has no proposed acceptance criterion.', req.id, severity));
  }
  for (const row of spec.unresolved) {
    const required = row.required || row.requirementIds.some((ref) => spec.requirements.some((req) => req.id === ref && req.required));
    issues.push(issue('unresolved-question', row.question.slice(0, 500), row.id, required ? 'blocking' : 'warning'));
  }
  for (const row of spec.unsupported) {
    const required = row.required || row.requirementIds.some((ref) => spec.requirements.some((req) => req.id === ref && req.required));
    issues.push(issue('unsupported-capability', row.reason.slice(0, 500), row.id, required ? 'blocking' : 'warning'));
  }
  return issues;
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    const row = value as Record<string, unknown>;
    return `{${Object.keys(row).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(row[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}
export function canonicalReviewContent(spec: GroundedBuildSpec, evidence: SpecEvidence): string {
  return canonicalJson({ spec, evidence: spec.requirements.flatMap((req) => req.citations.map((ref) => resolveCitation(ref, evidence))) });
}

const packSourceSchema = z.object({ version: z.literal('v0'), id: z.string(), video_id: videoIdSchema, source_url: z.string().max(2048), provenance: z.object({ source_hash: hash }) });
export function sourceForGroundedSpec(pack: unknown): GroundedBuildSpec['source'] | null {
  const parsed = packSourceSchema.safeParse(pack);
  if (!parsed.success) return null;
  const value = parsed.data;
  try {
    const url = new URL(value.source_url);
    const youtube = ['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(url.hostname);
    const urlId = url.hostname === 'youtu.be' ? url.pathname.slice(1) : youtube
      ? url.pathname === '/watch' ? url.searchParams.get('v') : /^\/(?:shorts|embed|v)\/([\w-]{11})$/.exec(url.pathname)?.[1]
      : null;
    if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password || url.port || urlId !== value.video_id || value.id !== `vp:v0:${value.video_id}`) return null;
  } catch { return null; }
  return { packId: value.id, videoId: value.video_id, sourceUrl: value.source_url, sourceHash: value.provenance.source_hash };
}

export function inspectGroundedSpec(pack: SpecEvidence & { grounded_spec?: unknown }): ReviewInspection {
  if (pack.grounded_spec === undefined) return { status: 'unavailable', issues: [] };
  const parsed = recordSchema.safeParse(pack.grounded_spec);
  if (!parsed.success) return { status: 'invalid', issues: shapeIssues(parsed.error) };
  if (parsed.data.status !== 'available') return parsed.data;
  const { spec, contentHash } = parsed.data;
  const source = sourceForGroundedSpec(pack);
  if (!source || canonicalJson(spec.source) !== canonicalJson(source)) return invalidGroundedSpec('Bound source identity does not match this pack.');
  const { source: _source, ...candidate } = spec;
  const checked = parseGroundedSpec(candidate, pack, source.videoId);
  if (!checked || checked.status !== 'available') return checked ?? invalidGroundedSpec('Specification is unavailable.');
  return { status: 'available', spec, contentHash, canonical: canonicalReviewContent(spec, pack), issues: specificationIssues(spec) };
}

export function decodeGroundedSpec(pack: SpecEvidence & { grounded_spec?: unknown }): GroundedSpecRecord | undefined {
  const result = inspectGroundedSpec(pack);
  if (result.status === 'unavailable') return undefined;
  if (result.status !== 'available') return { status: result.status, issues: result.issues };
  return { status: 'available', spec: result.spec, contentHash: result.contentHash };
}

export async function hashReviewContent(canonical: string): Promise<string> {
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
}
const acknowledgmentSchema = z.object({ version: z.literal('1'), sourceHash: hash, specHash: hash, acknowledgedAt: z.string().datetime() }).strict();
export type SpecReviewAcknowledgment = z.infer<typeof acknowledgmentSchema>;
export function reviewAcknowledgmentMatches(value: unknown, sourceHash: string, specHash: string): value is SpecReviewAcknowledgment {
  const parsed = acknowledgmentSchema.safeParse(value);
  return parsed.success && parsed.data.sourceHash === sourceHash && parsed.data.specHash === specHash;
}
