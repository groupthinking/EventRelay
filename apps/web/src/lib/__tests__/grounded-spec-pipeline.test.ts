import { describe, expect, it, vi } from 'vitest';
import { extractVideoPackSpec } from '@/lib/video-pack-extractor';
import { applyExtractedSpec, buildIdentityPack, GOLDEN_IDENTITY_HASHES } from '@/lib/video-pack';
import { verifyIdentityPack } from '@/lib/emit-video-pack';
import { browserSpecFixture } from '@/test/grounded-spec-fixture';

async function extract(raw: unknown) {
  return extractVideoPackSpec(
    { sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag', videoId: 'auJzb1D-fag' },
    { hasGatewayKey: () => true, generateText: vi.fn().mockResolvedValue({ text: typeof raw === 'string' ? raw : JSON.stringify(raw) }) },
  );
}

describe('grounded specification extraction boundary (synthetic source)', () => {
  it('binds source identity and transports a separately hashed review without changing pack identity', async () => {
    const pack = applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), await extract(browserSpecFixture()));
    expect(pack).toHaveProperty('grounded_spec.status', 'available');
    expect(pack).toHaveProperty('grounded_spec.contentHash', expect.stringMatching(/^[a-f0-9]{64}$/));
    expect(pack).toHaveProperty('grounded_spec.spec.source.videoId', 'auJzb1D-fag');
    expect(pack.provenance.source_hash).toBe(GOLDEN_IDENTITY_HASHES['auJzb1D-fag']);
    expect(verifyIdentityPack({ status: 'success', data: pack }).pack).toHaveProperty('grounded_spec', Reflect.get(pack, 'grounded_spec'));
  });

  it('does not promote missing raw timestamps through the legacy zero fallback', async () => {
    const raw = browserSpecFixture();
    Reflect.deleteProperty(raw.transcript.segments[0]!, 'start_s');
    const pack = applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), await extract(raw));
    expect(pack.transcript.segments[0]?.start_s).toBe(0);
    expect(pack).toHaveProperty('grounded_spec.status', 'invalid');
  });

  it.each([
    ['forged quote', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.requirements[0]!.citations[0]!.quote = 'Invented'; }],
    ['missing citation', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.requirements[0]!.citations = []; }],
    ['cross-video reference', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.requirements[0]!.citations[0]!.videoId = 'jNQXAC9IVRw'; }],
    ['negative timestamp', (r: ReturnType<typeof browserSpecFixture>) => { r.transcript.segments[0]!.start_s = -1; }],
    ['nonfinite timestamp', (r: ReturnType<typeof browserSpecFixture>) => { r.transcript.segments[0]!.start_s = Infinity; }],
    ['reversed timestamp', (r: ReturnType<typeof browserSpecFixture>) => { r.transcript.segments[0]!.end_s = 1; }],
    ['duplicate ID', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.screens.push(r.grounded_spec.screens[0]!); }],
    ['dangling reference', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.acceptanceCriteria[0]!.requirementId = 'missing'; }],
    ['unknown schema', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.version = '2'; }],
    ['missing honesty', (r: ReturnType<typeof browserSpecFixture>) => { Reflect.deleteProperty(r.grounded_spec, 'sourceStatus'); }],
    ['overlarge input', (r: ReturnType<typeof browserSpecFixture>) => { r.grounded_spec.app.name = 'a'.repeat(3000); }],
    ['model-provided authority', (r: ReturnType<typeof browserSpecFixture>) => { Reflect.set(r.grounded_spec, 'source', { videoId: 'forged' }); }],
  ] as const)('rejects %s without destroying legacy content', async (_, mutate) => {
    const raw = browserSpecFixture();
    mutate(raw);
    const pack = applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), await extract(raw));
    expect(pack.transcript.full_text).toBeTruthy();
    expect(pack).toHaveProperty('grounded_spec.status', 'invalid');
  });

  it('keeps repaired JSON usable only as legacy evidence', async () => {
    const raw = JSON.stringify(browserSpecFixture()).slice(0, -1);
    const pack = applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), await extract(raw));
    expect(pack.transcript.full_text).toBeTruthy();
    expect(pack).toHaveProperty('grounded_spec.status', 'invalid');
  });

  it('stops a no-source specification rather than inventing a blueprint', async () => {
    const raw = browserSpecFixture();
    raw.grounded_spec.sourceStatus = 'none';
    const pack = applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), await extract(raw));
    expect(pack).toHaveProperty('grounded_spec.status', 'source-unavailable');
    expect(Reflect.get(pack, 'grounded_spec')).not.toHaveProperty('spec');
  });

  it('preserves legacy packs without synthesizing grounding', async () => {
    const raw = browserSpecFixture();
    Reflect.deleteProperty(raw, 'grounded_spec');
    const pack = applyExtractedSpec(buildIdentityPack('auJzb1D-fag'), await extract(raw));
    expect(pack).not.toHaveProperty('grounded_spec');
    expect(verifyIdentityPack({ status: 'success', data: pack }).pack).not.toHaveProperty('grounded_spec');
  });

  it('asks for classified source-linked browser requirements in the single attached-video pass', async () => {
    const generateText = vi.fn().mockResolvedValue({ text: JSON.stringify(browserSpecFixture()) });
    await extractVideoPackSpec({ sourceUrl: 'https://www.youtube.com/watch?v=auJzb1D-fag', videoId: 'auJzb1D-fag' }, { hasGatewayKey: () => true, generateText });
    expect(generateText).toHaveBeenCalledTimes(1);
    const content = generateText.mock.calls[0]![0].messages[0].content;
    expect(content[0].type).toBe('file');
    expect(content[1].text).toContain('grounded_spec');
    expect(content[1].text).toContain('untrusted');
  });
});
