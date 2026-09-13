import { describe, expect, it } from 'vitest';
import { browserSpecFixture, reviewPackFixture } from '@/test/grounded-spec-fixture';
import { decodeGroundedSpec, hashReviewContent, inspectGroundedSpec, parseGroundedSpec, reviewAcknowledgmentMatches } from '@/lib/grounded-build-spec';

function inspect(pack = reviewPackFixture()) {
  const result = inspectGroundedSpec(pack);
  if (result.status !== 'available') throw new Error(JSON.stringify(result));
  return result;
}

describe('source review validation and content identity (synthetic)', () => {
  it('hashes identically in browser crypto and server crypto, independent of object key order', async () => {
    const pack = reviewPackFixture();
    const review = inspect(pack);
    expect(await hashReviewContent(review.canonical)).toBe(review.contentHash);
    expect(inspect(JSON.parse(JSON.stringify(pack))).canonical).toBe(review.canonical);
    if (pack.grounded_spec?.status !== 'available') throw new Error('Missing test spec');
    pack.grounded_spec.spec.app = { purpose: pack.grounded_spec.spec.app.purpose, name: pack.grounded_spec.spec.app.name };
    expect(inspect(pack).canonical).toBe(review.canonical);
  });
  it.each(['evidence', 'criterion', 'limitations', 'scope'] as const)('invalidates exact-content review when %s changes', async (field) => {
    const pack = reviewPackFixture();
    const before = inspect(pack);
    if (pack.grounded_spec?.status !== 'available') throw new Error('Missing test spec');
    const spec = pack.grounded_spec.spec;
    if (field === 'evidence') pack.transcript.segments[0]!.text += ' Extra source context.';
    if (field === 'criterion') spec.acceptanceCriteria[0]!.then += ' Updated.';
    if (field === 'limitations') spec.limitations.push('Additional limitation');
    if (field === 'scope') spec.requirements[0]!.capabilities.push('server');
    const after = inspect(pack);
    const hash = await hashReviewContent(after.canonical);
    expect(hash).not.toBe(before.contentHash);
    expect(reviewAcknowledgmentMatches({ version: '1', sourceHash: spec.source.sourceHash, specHash: before.contentHash, acknowledgedAt: new Date().toISOString() }, spec.source.sourceHash, hash)).toBe(false);
  });
  it('blocks unresolved required behavior even if its question claims to be optional', () => {
    const raw = browserSpecFixture();
    raw.grounded_spec.unresolved.push({ id: 'behavior', requirementIds: ['toggle'], question: 'Which state transition is required?', required: false });
    expect(inspect(reviewPackFixture(raw)).issues).toContainEqual(expect.objectContaining({ code: 'unresolved-question', severity: 'blocking' }));
  });
  it('keeps required backend and secret capabilities blocked, never substitutes local state', () => {
    const raw = browserSpecFixture();
    raw.grounded_spec.requirements[0]!.capabilities = ['server', 'secrets'];
    raw.grounded_spec.unsupported.push({ id: 'secret', requirementIds: ['toggle'], capability: 'secrets', reason: 'Requires server-side credentials; values are not requested.', required: true });
    const review = inspect(reviewPackFixture(raw));
    expect(review.issues.some((i) => i.code === 'unsupported-capability' && i.severity === 'blocking')).toBe(true);
    expect(review.spec.requirements[0]!.capabilities).toEqual(['server', 'secrets']);
  });
  it('does not create an application from a non-app source', () => {
    const raw = browserSpecFixture();
    raw.grounded_spec.app = { name: '', purpose: '' };
    raw.grounded_spec.requirements = [];
    raw.grounded_spec.screens = [];
    raw.grounded_spec.acceptanceCriteria = [];
    expect(parseGroundedSpec(raw.grounded_spec, raw, 'auJzb1D-fag')?.status).toBe('invalid');
  });
  it('treats visuals as descriptions and validates their real timestamps', () => {
    const raw = browserSpecFixture();
    raw.grounded_spec.requirements[0]!.citations = [{ kind: 'visual', index: 0, videoId: 'auJzb1D-fag', startSeconds: 5, endSeconds: 5, quote: 'A task list with checkboxes.' }];
    expect(inspect(reviewPackFixture(raw)).issues[0]!.message).toContain('not verified captured frames');
    Reflect.deleteProperty(raw.visual_context.visual_elements[0]!, 'timestamp');
    expect(parseGroundedSpec(raw.grounded_spec, raw, 'auJzb1D-fag')?.status).toBe('invalid');
  });
  it('revalidates identity, shape and citations at decoding', () => {
    const pack = reviewPackFixture();
    pack.video_id = 'jNQXAC9IVRw';
    expect(decodeGroundedSpec(pack)?.status).toBe('invalid');
    expect(decodeGroundedSpec({ grounded_spec: { status: 'available', spec: null } })?.status).toBe('invalid');
    expect(decodeGroundedSpec({})).toBeUndefined();
  });
  it('rejects malformed, wrong-version and stale local acknowledgment metadata', () => {
    const review = inspect();
    const ack = { version: '1', sourceHash: review.spec.source.sourceHash, specHash: review.contentHash, acknowledgedAt: new Date().toISOString() };
    expect(reviewAcknowledgmentMatches(ack, ack.sourceHash, ack.specHash)).toBe(true);
    for (const value of [null, {}, { ...ack, version: '2' }, { ...ack, acknowledgedAt: 'yesterday' }, { ...ack, specHash: '0'.repeat(64) }]) expect(reviewAcknowledgmentMatches(value, ack.sourceHash, ack.specHash)).toBe(false);
  });
});
